import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import logging
logging.getLogger('tensorflow').setLevel(logging.ERROR)

import matplotlib.pyplot as plt
import cv2
import matplotlib.image as mpimg

import tensorflow as tf
from tensorflow import keras

import numpy as np
import random

import colorsys
import PIL.Image as PILImage

from scipy.spatial import KDTree
from webcolors import hex_to_rgb

import tf_keras
from tf_keras.preprocessing import image as keras_image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sub_model = tf_keras.models.load_model(os.path.join(BASE_DIR, 'models', 'model_sub'))
top_model = tf_keras.models.load_model(os.path.join(BASE_DIR, 'models', 'model_top'))
bottom_model = tf_keras.models.load_model(os.path.join(BASE_DIR, 'models', 'model_bottom'))
foot_model = tf_keras.models.load_model(os.path.join(BASE_DIR, 'models', 'model_shoes'))


sub_list = ["bottom", "foot", "top"]

top_list = [['Belts', 'Blazers', 'Dresses', 'Dupatta', 'Jackets', 'Kurtas',
             'Kurtis', 'Lehenga Choli', 'Nehru Jackets', 'Rain Jacket',
             'Rompers', 'Shirts', 'Shrug', 'Suspenders', 'Sweaters',
             'Sweatshirts', 'Tops', 'Tshirts', 'Tunics', 'Waistcoat'],
            ['Boys', 'Girls', 'Men', 'Unisex', 'Women'],
            ['Black', 'Blue', 'Dark Blue', 'Dark Green', 'Dark Yellow', 'Green',
             'Grey', 'Light Blue', 'Multi', 'Orange', 'Pink', 'Purple', 'Red',
             'White', 'Yellow'],
            ['Fall', 'Spring', 'Summer', 'Winter'],
            ['Casual', 'Ethnic', 'Formal', 'Party', 'Smart Casual', 'Sports',
             'Travel']]

bottom_list = [['Capris', 'Churidar', 'Jeans', 'Jeggings', 'Leggings', 'Patiala',
                'Salwar', 'Salwar and Dupatta', 'Shorts', 'Skirts', 'Stockings',
                'Swimwear', 'Tights', 'Track Pants', 'Tracksuits', 'Trousers'],
               ['Boys', 'Girls', 'Men', 'Unisex', 'Women'],
               ['Black', 'Blue', 'Dark Blue', 'Dark Green', 'Dark Yellow', 'Grey',
                'Light Blue', 'Multi', 'Orange', 'Pink', 'Purple', 'Red', 'White',
                'Yellow'],
               ['Fall', 'Spring', 'Summer', 'Winter'],
               ['Casual', 'Ethnic', 'Formal', 'Smart Casual', 'Sports']]

foot_list = [['Casual Shoes', 'Flats', 'Flip Flops', 'Formal Shoes', 'Heels',
              'Sandals', 'Sports Sandals', 'Sports Shoes'],
             ['Boys', 'Girls', 'Men', 'Unisex', 'Women'],
             ['Black', 'Blue', 'Dark Blue', 'Dark Green', 'Dark Orange',
              'Dark Yellow', 'Grey', 'Light Blue', 'Multi', 'Orange', 'Pink',
              'Purple', 'Red', 'White', 'Yellow'],
             ['Fall', 'Spring', 'Summer', 'Winter'],
             ['Casual', 'Ethnic', 'Formal', 'Party', 'Smart Casual', 'Sports']]


def convert_rgb_to_names(rgb_tuple):
    import webcolors
    names = []
    rgb_values = []
    try:
        from webcolors import CSS3_HEX_TO_NAMES as css3_db
        for color_hex, color_name in css3_db.items():
            names.append(color_name)
            rgb_values.append(hex_to_rgb(color_hex))
    except ImportError:
        for name in webcolors.names("css3"):
            names.append(name)
            rgb_values.append(webcolors.name_to_rgb(name))

    kdt_db = KDTree(rgb_values)
    distance, index = kdt_db.query(rgb_tuple)
    return names[index]


def get_cloth_color(image):
    max_score = 0.0001
    dominant_color = None
    for count, (r, g, b) in image.getcolors(image.size[0] * image.size[1]):
        saturation = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)[1]
        y = min(abs(r * 2104 + g * 4130 + b * 802 + 4096 + 131072) >> 13, 235)
        y = (y - 16.0) / (235 - 16)
        if y > 0.9:
            continue
        score = (saturation + 0.1) * count
        if score > max_score:
            max_score = score
            dominant_color = (r, g, b)

    return convert_rgb_to_names(dominant_color)


def color_classification(single_path):
    image = PILImage.open(single_path)
    image = image.convert('RGB')
    return get_cloth_color(image)


def single_helper(train_images, my_model, lelist):
    my_predictions = my_model.predict(train_images)
    result = []
    type_predicted_label = np.argmax(my_predictions[0][0])
    result.append(lelist[0][type_predicted_label])
    type_predicted_label = np.argmax(my_predictions[1][0])
    result.append(lelist[1][type_predicted_label])
    type_predicted_label = np.argmax(my_predictions[2][0])
    result.append(lelist[2][type_predicted_label])
    type_predicted_label = np.argmax(my_predictions[3][0])
    result.append(lelist[3][type_predicted_label])
    type_predicted_label = np.argmax(my_predictions[4][0])
    result.append(lelist[4][type_predicted_label])
    return result


def single_classification(single_path):
    train_images = np.zeros((1, 80, 60, 3))

    path = single_path
    img = cv2.imread(path)

    if img is None or img.shape != (80, 60, 3):
        pil_img = keras_image.load_img(path, target_size=(80, 60))
        img = keras_image.img_to_array(pil_img)
    else:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    train_images[0] = img

    result2 = sub_list[np.argmax(sub_model.predict(train_images))]

    if result2 == "top":
        res = single_helper(train_images, top_model, top_list)
    elif result2 == "bottom":
        res = single_helper(train_images, bottom_model, bottom_list)
    elif result2 == "foot":
        res = single_helper(train_images, foot_model, foot_list)
    else:
        raise ValueError(f"Unexpected sub-model result: {result2}")

    res.append(single_path)
    res_str = f"{res[0]}, {res[1]}, {color_classification(single_path)}, {res[3]}, {res[4]}, {single_path}"

    return (result2, res_str, res)


def find_combo_by_top(top_color_group, combotype):
    co = int(combotype / 30)

    if top_color_group == 15:
        bottom_color_group = random.choice([12, 13, 14])
        if bottom_color_group == 12:
            shoes_color_group = 13
        elif bottom_color_group == 13:
            shoes_color_group = random.choice([12, 13, 14])
        else:
            shoes_color_group = random.choice([12, 13])

    elif top_color_group == 12 or top_color_group == 13 or top_color_group == 14:
        if top_color_group == 12:
            bottom_color_group = random.choice([12, 13])
            if bottom_color_group == 12:
                shoes_color_group = 13
            else:
                shoes_color_group = random.choice([12, 13])
        elif top_color_group == 13:
            bottom_color_group = random.choice([12, 13])
            if bottom_color_group == 12:
                shoes_color_group = 13
            else:
                shoes_color_group = 12
        else:
            bottom_color_group = random.choice([12, 13])
            shoes_color_group = random.choice([12, 13])
    else:
        bottom_color_group = random.choice([top_color_group - co, top_color_group + co])
        if bottom_color_group == top_color_group - co:
            shoes_color_group = top_color_group + co
        else:
            shoes_color_group = top_color_group - co

        if bottom_color_group == 12:
            bottom_color_group = 0
        if bottom_color_group == 13:
            bottom_color_group = 1
        if bottom_color_group == 14:
            bottom_color_group = 2
        if bottom_color_group == 15:
            bottom_color_group = 3
        if bottom_color_group == 16:
            bottom_color_group = 4
        if bottom_color_group == 17:
            bottom_color_group = 5

        if shoes_color_group == 12:
            shoes_color_group = 0
        if shoes_color_group == 13:
            shoes_color_group = 1
        if shoes_color_group == 14:
            shoes_color_group = 2
        if shoes_color_group == 15:
            shoes_color_group = 3
        if shoes_color_group == 16:
            shoes_color_group = 4
        if shoes_color_group == 17:
            shoes_color_group = 5

        if bottom_color_group == -1:
            bottom_color_group = 11
        if bottom_color_group == -2:
            bottom_color_group = 10
        if bottom_color_group == -3:
            bottom_color_group = 9
        if bottom_color_group == -4:
            bottom_color_group = 8
        if bottom_color_group == -5:
            bottom_color_group = 7
        if bottom_color_group == -6:
            bottom_color_group = 6

        if shoes_color_group == -1:
            shoes_color_group = 11
        if shoes_color_group == -2:
            shoes_color_group = 10
        if shoes_color_group == -3:
            shoes_color_group = 9
        if shoes_color_group == -4:
            shoes_color_group = 8
        if shoes_color_group == -5:
            shoes_color_group = 7
        if shoes_color_group == -6:
            shoes_color_group = 6

    return (bottom_color_group, shoes_color_group)


from datetime import date

todays_date = date.today()
tomonth = todays_date.month
if tomonth in [3, 4, 5]:
    toseason = "Spring"
elif tomonth in [6, 7, 8]:
    toseason = "Summer"
elif tomonth in [9, 10, 11]:
    toseason = "Fall"
else:
    toseason = "Winter"