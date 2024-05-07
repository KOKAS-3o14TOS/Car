from flask import Flask, Response, render_template
from picar import front_wheels, back_wheels
from picar.SunFounder_PCA9685 import Servo
import picar
from time import sleep
import cv2
import numpy as np
import picar
import os

picar.setup()

MIDDLE_TOLERANT = 5
PAN_ANGLE_MAX   = 180
PAN_ANGLE_MIN   = 0
TILT_ANGLE_MAX  = 180
TILT_ANGLE_MIN  = 0
FW_ANGLE_MAX    = 90+30
FW_ANGLE_MIN    = 90-30

SCAN_POS = [[20, TILT_ANGLE_MIN], [50, TILT_ANGLE_MIN], [90, TILT_ANGLE_MIN], [130, TILT_ANGLE_MIN], [160, TILT_ANGLE_MIN], 
            [160, 80], [130, 80], [90, 80], [50, 80], [20, 80]]

bw = back_wheels.Back_Wheels()
fw = front_wheels.Front_Wheels()
pan_servo = Servo.Servo(1)
tilt_servo = Servo.Servo(3)
picar.setup()

fw.offset = 10
pan_servo.offset = 0
tilt_servo.offset = 0
bw.speed = 60
pan_servo.write(90)
tilt_servo.write(22.5)
bw.stop()

app = Flask(__name__, template_folder='template')

# Función para detectar un color en una región específica de la imagen
def detect_color(image, lower_bound, upper_bound, t2,side):
    p=0
    key = False 
    # Convertir la imagen al espacio de color HSV
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    # Crear una máscara para el rango de colores especificado
    mask = cv2.inRange(hsv, lower_bound, upper_bound)
    # Encontrar contornos en la máscara
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Dibujar los contornos en la imagen original
    cv2.drawContours(image, contours, -1, (0, 255, 0), 2)

    for c in contours:
            #----AREA DE LOS CONTORNOS----
            area=cv2.contourArea(c)
            if area > 1500:

                #----Deteccion del centro----
                m=cv2.moments(c)
                if (m["m00"]==0): m['m00']=1
                x=int(m['m10']/m['m00'])
                y=int(m['m01']/m['m00'])

                if side == 'right':
                    p=abs(x)

                elif side == 'left':
                    p=abs(x-t2)
                    

                cv2.circle(image,(x,y),7,(0, 255, 0), -1)
                suavizacion_contorno=cv2.convexHull(c)
                cv2.drawContours(image, [suavizacion_contorno], 0, (255,0,0),2)
                key = True

    return key,p

def generate_frames():
    global bw
    global fw
    # Access the webcam
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        else:
            # Get frame dimensions
            height, width, _ = frame.shape
            t2 = width // 2
            
            # Define color range for detection(
            lower_bound = np.array([99, 160, 72], np.uint8)
            upper_bound = np.array([255, 255, 255], np.uint8)
           

            # Select each third and detect the corresponding color
            first_third = frame[:, :t2]
            second_third = frame[:, t2:2*t2]

            key1, p1 = detect_color(first_third, lower_bound, upper_bound, t2, 'left')
            key2, p2 = detect_color(second_third, lower_bound, upper_bound, t2, 'right')

            if key1 and key2:
                fw.turn(90)
                bw.speed = 30
                bw.forward()
            elif key1:
                x1 = 90-(p1/320)*90
                fw.turn(x1)
                bw.speed = 30
                bw.forward()
                
            elif key2:
                x2 = 90+(p2/320)*90
                fw.turn(x2)
                bw.speed = 30
                bw.forward()
                
            else:
                fw.turn(90)
                bw.stop()
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=55)