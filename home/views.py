from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import numpy as np
import base64
import numpy as np
import pandas as pd
import cv2
from keras.models import load_model
from PIL import Image
from docplex.cp.model import CpoModel


def extract_logic(image_data_url):
            _, encoded_image = image_data_url.split(",", 1)
            # Decode the base64 encoded image data
            decoded_image = base64.b64decode(encoded_image)
            
            sudoku_a = cv2.imdecode(np.frombuffer(decoded_image, np.uint8), cv2.IMREAD_COLOR)
            # sudoku_a_resized = cv2.resize(sudoku_a, (450, 450))

            # Save the resized image to a file
            image_path = "images/captured_image.png"
            
            def preprocess(image):
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                blur = cv2.GaussianBlur(gray, (3,3),6)
                    #blur = cv2.bilateralFilter(gray,9,75,75)
                threshold_img = cv2.adaptiveThreshold(blur,255,1,1,11,2)
                
                return threshold_img
            
            def main_outline(contour):
                biggest = np.array([])
                max_area = 0
                for i in contour:
                    area = cv2.contourArea(i)
                    if area >50:
                        peri = cv2.arcLength(i, True)
                        approx = cv2.approxPolyDP(i , 0.02* peri, True)
                        if area > max_area and len(approx) ==4:
                            biggest = approx
                            max_area = area
                return biggest ,max_area
            
            def reframe(points):
                points = points.reshape((4, 2))
                
                points_new = np.zeros((4,1,2),dtype = np.int32)
                add = points.sum(1)
                points_new[0] = points[np.argmin(add)]
                points_new[3] = points[np.argmax(add)]
                diff = np.diff(points, axis =1)
                points_new[1] = points[np.argmin(diff)]
                points_new[2] = points[np.argmax(diff)]
                
                return points_new
            
            def splitcells(img):
                rows = np.vsplit(img,9)
                boxes = []
                for r in rows:
                    cols = np.hsplit(r,9)
                    for box in cols:
                        boxes.append(box)
                return boxes
            
            su_puzzle=sudoku_a
            # height, width, _ = su_puzzle.shape
    
            # top_left = (0, 0)
            # bottom_right = (width - 1, height - 1)
            
            # # Draw the outermost rectangle (border)
            # su_puzzle = cv2.rectangle(su_puzzle.copy(), top_left, bottom_right, (0,0,0), 2)
           
            su_contour_1= su_puzzle.copy()
            su_contour_2= su_puzzle.copy()
            su_contour, hierarchy = cv2.findContours(preprocess(su_puzzle),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(su_contour_1, su_contour,-1,(0,255,0),3)
            
            black_img = np.zeros((450,450,3), np.uint8)
            su_biggest, su_maxArea = main_outline(su_contour)
            if su_biggest.size != 0:
                su_biggest = reframe(su_biggest)
                cv2.drawContours(su_contour_2,su_biggest,-1, (0,255,0),10)
                
                su_pts1 = np.float32(su_biggest)
                su_pts2 = np.float32([[0,0],[450,0],[0,450],[450,450]])
                su_matrix = cv2.getPerspectiveTransform(su_pts1,su_pts2)
                su_imagewrap = cv2.warpPerspective(su_puzzle,su_matrix,(450,450))
                su_imagewrap =cv2.cvtColor(su_imagewrap, cv2.COLOR_BGR2GRAY)
                
            _, buffer_detected = cv2.imencode('.png', su_imagewrap)
            detected_sudoku_encoded = base64.b64encode(buffer_detected).decode('utf-8')
            sudoku_cell = splitcells(su_imagewrap)
            # for cell_image in sudoku_cell:
            #     cv2.imshow('Cell Image', np.array(cell_image))
            #     cv2.waitKey(500)  # Wait for 3000 milliseconds (3 seconds)
            #     cv2.destroyAllWindows()
            
            def CropCell(cells):
                Cells_croped = []
                for image in cells:
                    img = np.array(image)
                    img = img[4:48, 6:46]
                    img = Image.fromarray(img)
                    Cells_croped.append(img)
                return Cells_croped
            
            sudoku_cell_croped= CropCell(sudoku_cell)
            # for cell_image in sudoku_cell_croped:
            #     cv2.imshow('Cell Image', np.array(cell_image))
            #     cv2.waitKey(500)  # Wait for 3000 milliseconds (3 seconds)
            #     cv2.destroyAllWindows()
            model = load_model('model/model6.h5')
            sudoku_cell_croped = CropCell(sudoku_cell)
            sudoku_grid = np.zeros((9, 9), dtype=int)
            
            for i in range(9):
                for j in range(9):
                    cell_image = np.array(sudoku_cell_croped[i * 9 + j])  # Convert to numpy array
                    # Use a simple thresholding to binarize the image
                    _, cell_threshold = cv2.threshold(cell_image, 128, 255, cv2.THRESH_BINARY)
                    # Invert the image (black background, white numbers)
                    cell_inverted = cv2.bitwise_not(cell_threshold)
                    cell_inverted=cv2.equalizeHist(cell_inverted)
                    # contours, _ = cv2.findContours(cell_inverted, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

                    # for contour in contours:
                    #     # Calculate the area of the contour
                    #     area = cv2.contourArea(contour)
                        
                    #     if area < 90:
                    #         cv2.drawContours(cell_inverted, [contour], -1, (0, 0, 0), thickness=cv2.FILLED)
                            
                    blurred_image = cv2.GaussianBlur(cell_inverted, (1, 1), 0)
                    # Apply bilateral filter for edge preservation and noise reduction
                    cell_inverted = cv2.bilateralFilter(blurred_image, 1, 100, 100)
                    
                    # cv2.imshow("Cell image",cell_inverted)
                    # cv2.waitKey(200)
                    # cv2.destroyAllWindows()
                    # Find contours in the cell image
                    # contours, _ = cv2.findContours(cell_inverted, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    # If contours are found, assume the cell contains a number
                    # if contours:
                        # contour_area = cv2.contourArea(contours[0])
                        # if contour_area > 10:  # Adjust the threshold as needed
                            # Extract the digit from the cell image
                    cell_digit = cv2.resize(cell_inverted, (28, 28))
                    cell_digit = cell_digit / 255.0  # Normalize the pixel values
                    cell_digit = cell_digit.reshape(28, 28, 1)
                    rgb_image = np.concatenate([cell_digit, cell_digit, cell_digit], axis=-1)  # Reshape for model input
                    rgb_image_batch = np.expand_dims(rgb_image, axis=0)
                    # Predict the digit using the trained model (replace `model` with your trained model)
                    images=np.vstack([rgb_image_batch])
                    predicted_digit = np.argmax(model.predict(images))
                    # print("Type: {}, Size: {}, Data type: {}".format(type(cell_digit), cell_digit.shape, cell_digit.dtype))
                    # Store the predicted digit in the sudoku grid
                    sudoku_grid[i][j] = predicted_digit
                            
            print(sudoku_grid)
            
            
            
            return sudoku_grid,detected_sudoku_encoded


def solve_logic(initial_sudoku):
            
            N = 9
            model = CpoModel()
            X = [[model.integer_var(1, N, f"X[{i+1}][{j+1}]") for j in range(N)] for i in range(N)]
            
            
            for i in range(N):
                model.add(model.all_diff([X[i][j] for j in range(N)]))
                model.add(model.all_diff([X[j][i] for j in range(N)]))

            for i in range(0, N, 3):
                for j in range(0, N, 3):
                    model.add(model.all_diff([X[i+di][j+dj] for di in range(3) for dj in range(3)]))

            for i in range(N):
                for j in range(N):
                    if initial_sudoku[i][j] != 0:
                        model.add(X[i][j] == initial_sudoku[i][j])
                
            
            solution = model.solve()
            return solution,X

# Create your views here.

def home(request):
    return JsonResponse({"message":"Server booted"}, status=200)

@csrf_exempt
def extract(request):
    if request.method == "POST":
        data = json.loads(request.body)
        image_data_url = data.get("imageDataURL")

        # Convert the flattened array to a 3D NumPy array (image format)
        if not image_data_url:
            return JsonResponse({"error": "No imageDataURL provided"}, status=400)

        try:
            # Extract image data from the data URL
            
            initial_sudoku , detected_sudoku_encoded= extract_logic(image_data_url)
            
            return JsonResponse({"Unsolved":json.dumps(initial_sudoku.tolist()), "Detected_encoded":detected_sudoku_encoded})
                
            

        except Exception as e:
            print(e)
            return JsonResponse({"error": str(e)}, status=500)

    else:
        return JsonResponse({"error": "Only POST requests are allowed"}, status=405)

@csrf_exempt
def solve(request):
    if request.method=="POST":
        data = json.loads(request.body)
        initial_sudoku = data.get("grid")
        sudoku_grid=initial_sudoku
        try:
            solution,X=solve_logic(initial_sudoku)
            if solution:
                solved_sudoku = []
                for row in X:
                    current_row = []
                    for cell in row:
                        current_row.append(solution.get_value(cell))
                    solved_sudoku.append(current_row)
                    
                solved_sudoku_array = np.array(solved_sudoku)
                print("The solved Sudoku:")
                print(solved_sudoku_array)
            else:
                print("No solution found.")
                
                
            
            
            sudoku_array =solved_sudoku_array
            hints_grid = sudoku_grid
           
            if(solution):
                return JsonResponse({"solved": json.dumps(sudoku_array.tolist())})
            else:
                return JsonResponse({"error": "No solution found. Try checking the values again"}, status=204)
        except Exception as e:
            return JsonResponse({"error": "No solution found. Try checking the values again"}, status=204)
        
        
        
            # def sudoku_to_image(sudoku_array, sudoku_grid):
            #     image = np.ones((454, 454, 3)) * 255  # White background with outer border

            #     # Define the dimensions of each cell and the grid thickness
            #     cell_size = 50
            #     grid_thickness = 2
            #     outer_border_thickness = 4  # Thickness of the outer border

            #     # Draw outer border
            #     cv2.rectangle(image, (0, 0), (453, 453), (0, 0, 0), outer_border_thickness)
                
            #     for i in range(9):
            #         for j in range(9):
            #             # Get the value of the cell
            #             cell_value = sudoku_array[i][j]

            #             # If the cell value is not zero, write it on the image
            #             if cell_value != 0:
            #                 # Calculate the position to write the cell value
            #                 x_pos = j * cell_size + 17
            #                 y_pos = i * cell_size + 35

            #                 # Determine the color based on sudoku_grid
            #                 if sudoku_grid[i][j] == cell_value:
            #                     color = (0, 0, 255)  # Red color for correct cells
            #                 else:
            #                     color = (0, 0, 0)  # Black color for incorrect cells

            #                 # Write the cell value on the image
            #                 cv2.putText(image, str(cell_value), (x_pos, y_pos), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1.5, color, 2)
                            
            #     for i in range(1, 9):
            #         if i % 3 == 0:
            #             thickness = 2 * grid_thickness
            #         else:
            #             thickness = grid_thickness

            #         # Draw horizontal grid lines
            #         cv2.line(image, (0, i * cell_size), (453, i * cell_size), (0, 0, 0), thickness)
            #         # Draw vertical grid lines
            #         cv2.line(image, (i * cell_size, 0), (i * cell_size, 453), (0, 0, 0), thickness)

            #     return image
            
            
            
            # sudoku_image = sudoku_to_image(sudoku_array, hints_grid)
            
            # _, buffer = cv2.imencode('.png', sudoku_image)
            # encoded_image = base64.b64encode(buffer).decode('utf-8')
   
            # Check if the image was saved successfully
            # if os.path.exists(image_path):