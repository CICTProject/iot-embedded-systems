import random

def read_temperature():
    return round(random.uniform(20.0, 35.0), 2)

def get_camera_feed():
    return {"resolution": "144p", "status": "streaming", "fov": "70mm"}

def set_fan_speed(speed):
    return {"actuator": "fan", "target_speed": speed, "status": "success"}