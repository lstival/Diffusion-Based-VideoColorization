import os
import torch
import torchvision
from PIL import Image
from matplotlib import pyplot as plt
# from torch.utils.data import DataLoader
from torchvision import transforms
from datetime import datetime
import kornia as K
# from ViT import Vit_neck

def plot_images(images):
    plt.figure(figsize=(32, 32))
    plt.imshow(torch.cat([
        torch.cat([i for i in images.cpu()], dim=-1),
    ], dim=-2).permute(1, 2, 0).cpu())
    plt.show()


def plot_images_2(pil_images):
    num_images = len(pil_images)
    fig, axes = plt.subplots(nrows=1, ncols=num_images, figsize=(num_images*4, 4))
    try:
        for i, ax in enumerate(axes):
            ax.imshow(pil_images[i])
            ax.axis('off')
    except:
        axes.imshow(pil_images[0])
    plt.show()

def save_images(images, path, **kwargs):
    try:
        grid = torchvision.utils.make_grid(images, **kwargs)
        ndarr = grid.permute(1, 2, 0).to('cpu').numpy()
        im = Image.fromarray(ndarr)
    except:
        im = images
    im.save(path)

def save_images_2(images, folder_path):
    widths, heights = zip(*(i.size for i in images))
    total_width = sum(widths)
    max_height = max(heights)
    new_im = Image.new('RGB', (total_width, max_height))

    x_offset = 0
    for im in images:
        new_im.paste(im, (x_offset, 0))
        x_offset += im.size[0]

    new_im.save(folder_path)

def setup_logging(run_name):
    os.makedirs("models", exist_ok=True)
    os.makedirs("results", exist_ok=True)
    os.makedirs(os.path.join("models", run_name), exist_ok=True)
    os.makedirs(os.path.join("results", run_name), exist_ok=True)

def create_samples(data, device="cuda", pos_imgs=False, constrative=False):
    """
    img: Image with RGB colors (ground truth)
    img_gray: Grayscale version of the img (this) variable will be used to be colorized
    img_color: the image with color that bt used as example (first at the scene)
    """

    # Test if the pos_color must be returned
    if len(data) == 4:
        img, img_color, next_frame, random_frame = data
        if isinstance(img, list):
            img, img_color, next_frame, random_frame = img[0], img_color[0], next_frame[0], random_frame[0]
    else:
        img, img_color, next_frame = data

        if isinstance(img, list):
            img, img_color, next_frame = img[0], img_color[0], next_frame[0]

    # img.to(device)
    # img_color.to(device)

    img_gray = transforms.Grayscale(num_output_channels=3)(img)
    # img_gray = img[:,:1,:,:]

    img = img.to(device)
    img_gray = img_gray.to(device)
    img_color = img_color.to(device)
    next_frame = next_frame.to(device)

    if len(data) == 4:
        random_frame = random_frame.to(device)
        return img, img_gray, img_color, next_frame, random_frame
    return img, img_gray, img_color, next_frame


def get_model_time():
    #to create the timestamp
    dt = datetime.now()
    # dt_str = datetime.timestamp(dt)

    dt_str = str(dt).replace(':','.')
    dt_str = datetime.now().strftime('%Y%m%d_%H%M%S')

    return dt_str

def tensor_2_img(img, int_8=True):
    if int_8:
        new_img = (((img.clamp(-1, 1) + 1) / 2)*255).type(torch.uint8)
    else:
        new_img = (((img.clamp(-1, 1) + 1) / 2))
    return new_img

def scale_0_and_1(tensor):
    """
    Recives a tensor and return their values between 0 and 1
    """
    tensor_min = tensor.min()
    tensor_max = tensor.max()
    tensor_rescaled = (tensor - tensor_min) / (tensor_max - tensor_min)

    return tensor_rescaled


def read_frames(image_folder, img_start_name=None):
    """
    Read all frames of the image_folder, salve it
    in a folder and return.
    """

    if img_start_name is not None:
        images = [img for img in os.listdir(image_folder) if (img.endswith(".png") and img.startswith(img_start_name))]

        if images == []:
            images = [img for img in os.listdir(image_folder) if (img.endswith(".jpg") and img.startswith(img_start_name))]

    else:
        images = [img for img in os.listdir(image_folder) if img.endswith(".png")]

        if images == []:
            images = [img for img in os.listdir(image_folder) if img.endswith(".jpg")]

    return images

def frame_2_video(image_folder, video_name, img_start_name, gray=False, frame_rate=16):
    """
    Get the path with the frames and the name that video must be
    and create and save the video.
    """
    import cv2
    fourcc = cv2.VideoWriter_fourcc(*'MP4V')

    images = read_frames(image_folder, img_start_name)
        
    frame = cv2.imread(os.path.join(image_folder, images[0]))
    height, width, layers = frame.shape

    if gray == True:
        video = cv2.VideoWriter(video_name, fourcc, frame_rate, (width,height), 0)
    else:
        video = cv2.VideoWriter(video_name, fourcc, frame_rate, (width,height))

    for image in images:
        temp_image = cv2.imread(os.path.join(image_folder, image), 1)
        
        if gray == True:
            temp_image = cv2.cvtColor(temp_image, cv2.COLOR_BGR2GRAY)
        video.write(temp_image)

    video.release()
    # print("Convertion Done")

def tensor_lab_2_rgb(x, int_8=True):
    try:
        y,u,v = torch.split(x, 1, dim=1)
    except:
        _, y,u,v = torch.split(x, 1, dim=1)

    y = scale_0_and_1(y)

    u = (u.clamp(-1, 1) + 1) / 2
    v = (v.clamp(-1, 1) + 1) / 2

    u = (u - 0.5)
    v = (v - 0.5)
    x = torch.cat([y, u, v], 1)

    x = K.color.yuv_to_rgb(x)
    if int_8:
        x = (scale_0_and_1(x)*255).type(torch.uint8)
    else:
        x = (scale_0_and_1(x))

    return x

def create_gray_videos(dataset, path_video_save, data_mode="train"):

    images_paths = f"./data/{data_mode}/{dataset}"
    img_classes = os.listdir(images_paths)

    os.makedirs(path_video_save, exist_ok=True)

    for v_class in img_classes:

        image_folder = f"./data/{data_mode}/{dataset}/{v_class}"
        
        video_name = f'{path_video_save}{v_class}.mp4'

        frame_2_video(image_folder, video_name, img_start_name=None, gray=True)

    assert len(img_classes) == len(os.listdir(path_video_save)), "Created videos must be same amout of files that video classes."

    print("Gray videos created")

def delete_empty_folders(root_dir):
    """
    Dele all empty folder present in the passed dir
    """
    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
        for dirname in dirnames:
            folder_path = os.path.abspath(os.path.join(dirpath, dirname))
            try:
                os.rmdir(folder_path)
                print(f"Deleted empty folder: {folder_path}")
            except OSError:
                pass

def load_trained_weights(model, model_name, file_name, model_path="unet_model"):
    """
    model: Instance of a model to get trained weights
    model_name: Name of trained model (name of the fold with the files)
    file_name: Name of the file with the weigths

    return the model with the trained weights.
    """

    #Path to load the saved weights 
    path_weights = os.path.join(model_path, model_name, f"{file_name}.pt")
    # Load the weights
    model_wights = torch.load(path_weights)
    # Instance the weights loaded to the model recivied from parameter
    model.load_state_dict(model_wights)

    return model

def resume(model, filename):
    model.load_state_dict(torch.load(filename))

def checkpoint(model, filename):
    torch.save(model.state_dict(), filename)

def weights_regularization(model, loss):
    """"
    Recives a model and loss of the acutal training epoch, and
    calculate de l1_penalty to avoid overfit.
    """

    l1_penalty = torch.nn.L1Loss(size_average=False)
    reg_loss = 0

    for param in model.parameters():
        reg_loss += l1_penalty(param)

    factor = 0.001 #lambda
    loss += factor * reg_loss

    return loss

def is_notebook():
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False      # Probably standard Python interpreter
    
def python_files():
    files_names = []

    path = "."
    # Lista os arquivos no diretório
    files = os.listdir(path)

    # Percorre os arquivos
    for file in files:
        # Verifica se o arquivo tem final .py
        if file.endswith(".py"):
        # Imprime o caminho do arquivo
            files_names.append(os.path.join(path, file))

    # Busca os arquivos em subpastas
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            if filename.endswith(".py"):
                # Imprime o caminho do arquivo
                files_names.append(os.path.join(dirpath, filename))

    return files_names
