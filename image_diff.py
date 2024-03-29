from PIL import Image
import numpy as np

def calculate_image_difference(img1, img2):
    if img1 == None or img2 == None:
        return 0
    img2 = img2.resize(img1.size, Image.NEAREST)
    
    # Convert images to NumPy arrays
    img1_array = np.asarray(img1)
    img2_array = np.asarray(img2)
    
    # Calculate the absolute difference between the images
    diff = np.abs(img1_array - img2_array)
    
    # Calculate the percentage of difference
    num_diff_pixels = np.sum(diff > 0)  # Count pixels that are different
    total_pixels = np.prod(img1.size) * 3  # Total number of values in the array
    percent_diff = (num_diff_pixels / total_pixels) * 100
    return percent_diff

    

def calculate_image_file_difference(img_path1, img_path2):
    # Open the images
    img1 = Image.open(img_path1).convert('RGB')
    img2 = Image.open(img_path2).convert('RGB')
    
    percent_diff = calculate_image_difference(img1, img2)

    return percent_diff

if __name__ == "__main__":
    # Example usage
    img_path1 = 'window_capture.jpg'
    img_path2 = 'screen_capture.jpg'
    percent_diff = calculate_image_file_difference(img_path1, img_path2)
    print(f'Images differ by {percent_diff:.2f}%')

    # Decide whether to call OCR based on the difference
    if percent_diff > 10:
        print("Images are more than 10% different. Proceed with OCR.")
    else:
        print("Difference is less than 10%. No need to call OCR again.")
