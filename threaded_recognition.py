import logging
import os

import requests
import numpy as np
import face_recognition
from imutils.video import VideoStream
from imutils.video import FPS
from picamera.array import PiRGBArray
from picamera import PiCamera
import imutils
import time

DOOR_URL = 'http://door.gowombat.team/open/'


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')


def open_door():
    r = requests.post(DOOR_URL)
    if r.status_code == 200:
        door_opened = r.json()['success']
        if door_opened:
            time.sleep(5)

    time.sleep(1)


def get_or_create_face_encoding(image_filename):
    image_filepath = 'known_faces/' + image_filename
    encoding_filepath = 'known_encodings/' + os.path.splitext(image_filename)[0] + '.npy'

    face_encoding = None
    if os.path.exists(encoding_filepath):
        try:
            face_encoding = np.load(encoding_filepath)
            logging.info("Loaded saved encoding for {}".format(image_filename.split('.')[0]))
        except OSError:
            logging.info("Saved encoding for {} is broken".format(image_filename.split('.')[0]))
            os.remove(encoding_filepath)

    if face_encoding is None:
        face_image = face_recognition.load_image_file(image_filepath)
        face_encoding = face_recognition.face_encodings(face_image)[0]
        logging.info("Created encoding for {}".format(image_filename.split('.')[0]))

        np.save(encoding_filepath, face_encoding)
        logging.info("Saved encoding for {}".format(image_filename.split('.')[0]))

    return face_encoding



# initialize the camera and stream
camera = PiCamera()
camera.resolution = (320, 240)
camera.framerate = 32
camera.vflip = True
rawCapture = PiRGBArray(camera, size=(320, 240))
stream = camera.capture_continuous(rawCapture, format="bgr",
                                   use_video_port=True)


known_faces_names = []
known_faces = []

logging.info("Loading known face image(s)")
for filename in os.listdir('known_faces'):
    known_faces_names.append(filename.split('.')[0])
    known_faces.append(get_or_create_face_encoding(filename))


vs = VideoStream(usePiCamera=True).start()
time.sleep(2.0)

fps = FPS().start()
while True:
    frame = vs.read()

    face_locations = face_recognition.face_locations(frame)
    logging.info("Found {} faces in image.".format(len(face_locations)))
    face_encodings = face_recognition.face_encodings(frame, face_locations)

    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(known_faces, face_encoding)
        name = "<Unknown Person>"

        if True in matches:
            first_match_index = matches.index(True)
            name = known_faces_names[first_match_index]

            logging.info("Opening door for {}!".format(name))
            open_door()

    fps.update()
    logging.info("FPS: {}".format(fps.fps()))

# do a bit of cleanup
vs.stop()
fps.stop()
