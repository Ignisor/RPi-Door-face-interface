import io
import os
import logging
import threading

import face_recognition
import picamera
import numpy as np
import requests
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
            logging.info("Loaded saved encoding for {}".format(filename.split('.')[0]))
        except OSError:
            logging.info("Saved encoding for {} is broken".format(filename.split('.')[0]))
            os.remove(encoding_filepath)

    if face_encoding is None:
        face_image = face_recognition.load_image_file(image_filepath)
        face_encoding = face_recognition.face_encodings(face_image)[0]
        logging.info("Created encoding for {}".format(filename.split('.')[0]))

        np.save(encoding_filepath, face_encoding)
        logging.info("Saved encoding for {}".format(filename.split('.')[0]))

    return face_encoding


# camera = picamera.PiCamera()
# camera.resolution = (320, 240)
# camera.framerate = 30
# camera.vflip = True
# output = np.empty((240, 320, 3), dtype=np.uint8)

known_faces_names = []
known_faces = []

logging.info("Loading known face image(s)")
for filename in os.listdir('known_faces'):
    known_faces_names.append(filename.split('.')[0])
    known_faces.append(get_or_create_face_encoding(filename))


# while True:
#     logging.info("Capturing image.")
#     camera.capture(output, format="rgb")
#
#     face_locations = face_recognition.face_locations(output)
#     logging.info("Found {} faces in image.".format(len(face_locations)))
#     face_encodings = face_recognition.face_encodings(output, face_locations)
#
#     for face_encoding in face_encodings:
#         matches = face_recognition.compare_faces(known_faces, face_encoding)
#         name = "<Unknown Person>"
#
#         if True in matches:
#             first_match_index = matches.index(True)
#             name = known_faces_names[first_match_index]
#
#             logging.info("Opening door for {}!".format(name))
#             open_door()

# Create a pool of image processors
done = False
lock = threading.Lock()

class ImageProcessor(threading.Thread):
    def __init__(self):
        super(ImageProcessor, self).__init__()
        self.stream = io.BytesIO()
        self.event = threading.Event()
        self.terminated = False
        self.start()

    def run(self):
        # This method runs in a separate thread
        global done
        while not self.terminated:
            # Wait for an image to be written to the stream
            if self.event.wait(1):
                try:
                    self.stream.seek(0)
                    output = np.asarray(bytearray(self.stream.read()), dtype=np.uint8)

                    face_locations = face_recognition.face_locations(output)
                    logging.info("Found {} faces in image.".format(len(face_locations)))
                    face_encodings = face_recognition.face_encodings(output, face_locations)

                    for face_encoding in face_encodings:
                        matches = face_recognition.compare_faces(known_faces, face_encoding)

                        if True in matches:
                            first_match_index = matches.index(True)
                            name = known_faces_names[first_match_index]

                            logging.info("Opening door for {}!".format(name))
                            open_door()

                finally:
                    # Reset the stream and event
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()
                    # Return ourselves to the pool
                    with lock:
                        pool.append(self)


def streams():
    while not done:
        with lock:
            if pool:
                processor = pool.pop()
            else:
                processor = None
        if processor:
            yield processor.stream
            processor.event.set()
        else:
            # When the pool is starved, wait a while for it to refill
            time.sleep(0.1)


with picamera.PiCamera() as camera:
    pool = [ImageProcessor() for i in range(4)]
    camera.resolution = (320, 240)
    camera.framerate = 30
    camera.vflip = True
    camera.start_preview()
    time.sleep(2)
    camera.capture_sequence(streams(), use_video_port=True)


# Shut down the processors in an orderly fashion
while pool:
    with lock:
        processor = pool.pop()
    processor.terminated = True
    processor.join()
