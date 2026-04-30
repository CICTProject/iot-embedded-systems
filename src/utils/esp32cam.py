"""
Configuration module for ESP32 Camera settings.
Defines default values and helper functions for camera configuration.
"""

# ESP32 Camera Connection Defaults
ESP32_DEFAULT_HOST = "192.168.1.100"
ESP32_DEFAULT_PORT = 80

# ESP32 Web Server Endpoints
ESP32_ENDPOINTS = {
    "metadata": "/api/camera",                  # GET camera metadata and status
    "control": "/api/camera/control",           # POST camera settings control
    "reboot": "/api/camera/reboot",             # POST reboot device
    "sdcard_save": "/api/camera/sdcard/save",   # POST save image to SD card
    "sdcard_list": "/api/camera/sdcard/list",   # GET list SD card files
    "stream": "/_stream",                       # MJPEG stream
    "capture": "/_capture",                     # Capture single image
}

# Common Camera Settings (OV2640 sensor values)
CAMERA_FRAMESIZE = {
    "96x96": 0,      # FRAMESIZE_96X96
    "QQVGA": 1,      # 160x120
    "QCIF": 2,       # 176x144
    "HQVGA": 3,      # 240x176
    "240x240": 4,    # FRAMESIZE_240X240
    "QVGA": 5,       # 320x240
    "CIF": 6,        # 400x296
    "HVGA": 7,       # 480x360
    "VGA": 8,        # 640x480
    "SVGA": 9,       # 800x600
    "XGA": 10,       # 1024x768
    "HD": 11,        # 1280x720
    "SXGA": 12,      # 1280x1024
    "UXGA": 13,      # 1600x1200
}

# Quality Settings (JPEG compression)
CAMERA_QUALITY = {
    "high": 10,      # Better quality, larger file
    "medium": 20,
    "low": 40,       # More compression, smaller file
}

# Brightness Settings (-2 to +2)
CAMERA_BRIGHTNESS = {
    "very_dark": -2,
    "dark": -1,
    "normal": 0,
    "bright": 1,
    "very_bright": 2,
}

# Contrast Settings (-2 to +2)
CAMERA_CONTRAST = {
    "low": -2,
    "medium_low": -1,
    "normal": 0,
    "medium_high": 1,
    "high": 2,
}

# Saturation Settings (-2 to +2)
CAMERA_SATURATION = {
    "low": -2,
    "medium_low": -1,
    "normal": 0,
    "medium_high": 1,
    "high": 2,
}


def get_default_camera_settings() -> dict:
    """
    Get default camera configuration suitable for most use cases.
    """
    return {
        "framesize": CAMERA_FRAMESIZE["VGA"],        # 640x480
        "quality": CAMERA_QUALITY["medium"],          # Good balance
        "brightness": CAMERA_BRIGHTNESS["normal"],    # Normal lighting
        "contrast": CAMERA_CONTRAST["normal"],        # Normal contrast
        "saturation": CAMERA_SATURATION["normal"],    # Normal saturation
        "gainceiling": 4,                             # AGC ceiling
        "colorbar": False,                            # Show color bar test
        "whitebal": True,                             # Auto white balance
        "awb_gain": True,                             # Auto white balance gain
        "aec": True,                                  # Auto exposure control
        "aec2": False,                                # Auto exposure control 2
        "ae_level": 0,                                # Exposure level
        "aec_value": 300,                             # Exposure value
        "agc": True,                                  # Auto gain control
        "agc_gain": 5,                                # Auto gain value
        "bpc": False,                                 # Black pixel correction
        "wpc": True,                                  # White pixel correction
        "raw_gma": True,                              # Raw gamma
        "lenc": True,                                 # Lens correction
        "hmirror": False,                             # Horizontal mirror
        "vflip": False,                               # Vertical flip
        "dcw": True,                                  # DCW
        "colorspace": 0,                              # Color space
    }


def create_custom_settings(
    framesize: str = "VGA",
    quality: str = "medium",
    brightness: str = "normal",
    contrast: str = "normal",
    saturation: str = "normal",
    **kwargs
) -> dict:
    """
    Create custom camera settings.
    
    Args:
        framesize: Image resolution (key from CAMERA_FRAMESIZE)
        quality: JPEG quality (key from CAMERA_QUALITY)
        brightness: Brightness level (key from CAMERA_BRIGHTNESS)
        contrast: Contrast level (key from CAMERA_CONTRAST)
        saturation: Saturation level (key from CAMERA_SATURATION)
        **kwargs: Additional camera parameters
        
    Returns:
        Dictionary of camera settings
    """
    settings = get_default_camera_settings()
    
    # Update with provided parameters
    if framesize in CAMERA_FRAMESIZE:
        settings["framesize"] = CAMERA_FRAMESIZE[framesize]
    if quality in CAMERA_QUALITY:
        settings["quality"] = CAMERA_QUALITY[quality]
    if brightness in CAMERA_BRIGHTNESS:
        settings["brightness"] = CAMERA_BRIGHTNESS[brightness]
    if contrast in CAMERA_CONTRAST:
        settings["contrast"] = CAMERA_CONTRAST[contrast]
    if saturation in CAMERA_SATURATION:
        settings["saturation"] = CAMERA_SATURATION[saturation]
    
    # Apply any additional custom settings
    settings.update(kwargs)
    
    return settings

def get_esp32_url(host: str = ESP32_DEFAULT_HOST, port: int = ESP32_DEFAULT_PORT) -> str:
    """Construct the base URL for ESP32 camera HTTP server."""
    return f"http://{host}:{port}"
