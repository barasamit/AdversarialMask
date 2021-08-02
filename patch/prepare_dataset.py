from facenet_pytorch import MTCNN
import os
from PIL import Image

from shutil import copyfile
from collections import Counter

from tqdm import tqdm
import cv2
import numpy as np
from skimage import transform as trans
from pathlib import Path


def face_crop_raw_images_from_lab_cameras(input_path, output_path):
    tform = trans.SimilarityTransform()
    mtcnn = MTCNN()
    arcface_src = np.array(
        [[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366],
         [41.5493, 92.3655], [70.7299, 92.2041]],
        dtype=np.float32)
    p = Path(input_path)
    for image_path in tqdm(p.glob('**/*.jpg')):
        img = cv2.imread(os.path.join(input_path, image_path.name))
        # mtcnn(img, save_path=os.path.join(output_path, folder_name, image_path))
        boxes, _, points = mtcnn.detect(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), landmarks=True)
        if boxes is None:
            print('Face not found {}'.format(image_path.name))
            continue
        tform.estimate(points[0], arcface_src)
        M = tform.params[0:2, :]
        cut = cv2.warpAffine(img, M, (112, 112))

        cv2.imwrite(os.path.join(output_path, image_path.name), cut)


# face_crop_raw_images_from_lab_cameras('../data/gmail', '../datasets/persons/alon/train_new')


def face_crop_raw_images(input_path, output_path):
    tform = trans.SimilarityTransform()
    mtcnn = MTCNN(image_size=112, selection_method='center_weighted_size')
    arcface_src = np.array(
        [[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366],
         [41.5493, 92.3655], [70.7299, 92.2041]],
        dtype=np.float32)
    most_common = {}
    for folder_name in tqdm(os.listdir(input_path)):
        most_common[os.path.join(input_path, folder_name)] = len(os.listdir(os.path.join(input_path, folder_name)))
    most_common = [key.split('\\')[-1] for key, _ in sorted(most_common.items(), key=lambda item: item[1], reverse=True)]
    for folder_name in most_common:
        Path(os.path.join(output_path, folder_name)).mkdir(parents=True, exist_ok=True)
        for image_path in os.listdir(os.path.join(input_path, folder_name)):
            image = cv2.imread(os.path.join(input_path, folder_name, image_path))
            _, _, points = mtcnn.detect(cv2.cvtColor(image, cv2.COLOR_BGR2RGB), landmarks=True)
            if points is not None:
                p = points[0]
                tform.estimate(p, arcface_src)
                M = tform.params[0:2, :]
                cut = cv2.warpAffine(image, M, (112, 112))
                cv2.imwrite(os.path.join(output_path, folder_name, image_path), cut)


# face_crop_raw_images('../datasets/CelebA', '../datasets/CelebA_aligned')


def strip_lfw(input_path, output_path):
    for folder_name in os.listdir(input_path):
        for image_path in os.listdir(os.path.join(input_path, folder_name)):
            copyfile(os.path.join(input_path, folder_name, image_path), os.path.join(output_path, image_path))




# face_crop_raw_images('../datasets/lfw.csv', '../datasets/lfw_cropped')
# strip_lfw('../datasets/lfw.csv', '../datasets/lfw_strip')


def create_celeb_folders(root_path):
    lab_dict = {}
    target_folder = '../datasets/celebA'
    with open(os.path.join(root_path, 'identity_CelebA.txt'), 'r') as lab_file:
        for line in tqdm(lab_file):
            [image_name, celeb_lab] = line.split()
            lab_dict[image_name] = celeb_lab
            Path(os.path.join(target_folder, celeb_lab)).mkdir(parents=True, exist_ok=True)

    for image in tqdm(os.listdir(os.path.join(root_path, 'img_celeba'))):
        copyfile(os.path.join(root_path, 'img_celeba', image), os.path.join(target_folder, lab_dict[image], image))


# create_celeb_folders('../datasets/C/CelebA/Img')
