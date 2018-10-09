import os
import logging

import face_recognition
import picamera
import numpy as np
import requests
import time

DOOR_URL = 'http://door.gowombat.team/open/'


logging.basicConfig(level=logging.INFO)


def open_door():
    r = requests.post(DOOR_URL)
    if r.status_code == 200:
        door_opened = r.json()['success']
        if door_opened:
            time.sleep(5)

    time.sleep(1)

camera = picamera.PiCamera()
camera.resolution = (320, 240)
camera.vflip = True
output = np.empty((240, 320, 3), dtype=np.uint8)

known_faces_names = []
known_faces = []

logging.info("Loading known face image(s)")
for filename in os.listdir('known_faces'):
    filepath = 'known_faces/' + filename
    face_image = face_recognition.load_image_file(filepath)
    known_faces_names.append(filename.split('.')[0])
    known_faces.append(face_recognition.face_encodings(face_image)[0])
    logging.info("Loaded {}".format(filename.split('.')[0]))


while True:
    logging.info("Capturing image.")
    camera.capture(output, format="rgb")

    face_locations = face_recognition.face_locations(output)
    logging.info("Found {} faces in image.".format(len(face_locations)))
    face_encodings = face_recognition.face_encodings(output, face_locations)

    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(known_faces, face_encoding)
        name = "<Unknown Person>"

        if True in matches:
            first_match_index = matches.index(True)
            name = known_faces_names[first_match_index]

            logging.info("Opening door for {}!".format(name))
            open_door()
