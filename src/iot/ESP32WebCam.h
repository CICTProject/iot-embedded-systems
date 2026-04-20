#ifndef ESP32WEBCAM_H
#define ESP32WEBCAM_H

#include "esp_camera.h"
#include "esp_http_server.h"
#include <Arduino.h>

#define PART_BOUNDARY "123456789000000000000987654321"

#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

struct StreamContext {
    volatile bool* isActive;   
};

namespace ESP32Cam {
    enum CameraModel { CAMERA_MODEL_AI_THINKER };
}

static esp_err_t capture_handler(httpd_req_t* req) {
    auto* ctx = reinterpret_cast<StreamContext*>(req->user_ctx);
    if (ctx && ctx->isActive && !(*ctx->isActive)) {
        httpd_resp_set_status(req, "403 Forbidden");
        httpd_resp_set_type(req, "application/json");
        httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
        httpd_resp_sendstr(req, "{\"error\":\"Camera disabled\"}");
        return ESP_FAIL;
    }

    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }

    httpd_resp_set_type(req, "image/jpeg");
    httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_set_hdr(req, "Cache-Control", "no-cache, no-store, must-revalidate");

    esp_err_t res = httpd_resp_send(req, (const char*)fb->buf, (ssize_t)fb->len);
    esp_camera_fb_return(fb);
    return res;
}

static esp_err_t stream_handler(httpd_req_t* req) {
    auto* ctx = reinterpret_cast<StreamContext*>(req->user_ctx);

    if (ctx && ctx->isActive && !(*ctx->isActive)) {
        httpd_resp_set_status(req, "403 Forbidden");
        httpd_resp_set_type(req, "application/json");
        httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
        httpd_resp_sendstr(req, "{\"error\":\"Camera disabled\"}");
        return ESP_FAIL;
    }

    camera_fb_t* fb          = nullptr;
    uint8_t*     jpg_buf     = nullptr;
    size_t       jpg_buf_len = 0;
    bool         jpg_alloc   = false;   
    esp_err_t    res         = ESP_OK;
    char         part_buf[128];

    httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=" PART_BOUNDARY);
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_set_hdr(req, "Cache-Control", "no-cache, no-store, must-revalidate");
    httpd_resp_set_hdr(req, "Pragma", "no-cache");

    while (true) {
        if (ctx && ctx->isActive && !(*ctx->isActive)) {
            break;
        }

        fb = esp_camera_fb_get();
        if (!fb) {
            Serial.println("[STREAM] esp_camera_fb_get() failed");
            res = ESP_FAIL;
            break;
        }

        jpg_alloc = false;
        if (fb->format != PIXFORMAT_JPEG) {
            bool ok = frame2jpg(fb, 80, &jpg_buf, &jpg_buf_len);
            esp_camera_fb_return(fb);
            fb = nullptr;
            if (!ok) {
                Serial.println("[STREAM] frame2jpg conversion failed");
                res = ESP_FAIL;
                break;
            }
            jpg_alloc = true;
        } else {
            jpg_buf     = fb->buf;
            jpg_buf_len = fb->len;
        }

        // --- Gửi multipart header ---
        size_t hlen = (size_t)snprintf(
            part_buf, sizeof(part_buf),
            "\r\n--" PART_BOUNDARY
            "\r\nContent-Type: image/jpeg"
            "\r\nContent-Length: %u\r\n\r\n",
            (unsigned)jpg_buf_len
        );
        res = httpd_resp_send_chunk(req, part_buf, (ssize_t)hlen);

        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, (const char*)jpg_buf, (ssize_t)jpg_buf_len);
        }

        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, "\r\n", 2);
        }

        if (jpg_alloc) {
            free(jpg_buf);
            jpg_buf   = nullptr;
            jpg_alloc = false;
        } else if (fb) {
            esp_camera_fb_return(fb);
            fb = nullptr;
        }

        if (res != ESP_OK) break;
    }

    if (jpg_alloc && jpg_buf) {
        free(jpg_buf);
    }
    if (fb) {
        esp_camera_fb_return(fb);
    }

    return res;
}

class ESP32WebCam {
private:
    int             streamPort   = 81;
    httpd_handle_t  stream_httpd = nullptr;
    StreamContext   streamCtx;              

public:
    explicit ESP32WebCam(ESP32Cam::CameraModel model) {
        (void)model;  
    }

    esp_err_t sensorInit() {
        camera_config_t config = {};
        config.ledc_channel  = LEDC_CHANNEL_0;
        config.ledc_timer    = LEDC_TIMER_0;
        config.pin_d0        = Y2_GPIO_NUM;
        config.pin_d1        = Y3_GPIO_NUM;
        config.pin_d2        = Y4_GPIO_NUM;
        config.pin_d3        = Y5_GPIO_NUM;
        config.pin_d4        = Y6_GPIO_NUM;
        config.pin_d5        = Y7_GPIO_NUM;
        config.pin_d6        = Y8_GPIO_NUM;
        config.pin_d7        = Y9_GPIO_NUM;
        config.pin_xclk      = XCLK_GPIO_NUM;
        config.pin_pclk      = PCLK_GPIO_NUM;
        config.pin_vsync     = VSYNC_GPIO_NUM;
        config.pin_href      = HREF_GPIO_NUM;
        config.pin_sccb_sda  = SIOD_GPIO_NUM;
        config.pin_sccb_scl  = SIOC_GPIO_NUM;
        config.pin_pwdn      = PWDN_GPIO_NUM;
        config.pin_reset     = RESET_GPIO_NUM;
        config.xclk_freq_hz  = 20000000;
        config.pixel_format  = PIXFORMAT_JPEG;

        if (psramFound()) {
            config.frame_size   = FRAMESIZE_UXGA;
            config.jpeg_quality = 10;
            config.fb_count     = 2;

            config.grab_mode    = CAMERA_GRAB_LATEST;
        } else {
            config.frame_size   = FRAMESIZE_SVGA;
            config.jpeg_quality = 12;
            config.fb_count     = 1;
            config.grab_mode    = CAMERA_GRAB_WHEN_EMPTY;
        }

        return esp_camera_init(&config);
    }

    int getServerPort() const { return streamPort; }

    esp_err_t startCameraServer(volatile bool* activeFlag = nullptr) {
        streamCtx.isActive = activeFlag;

        httpd_config_t config   = HTTPD_DEFAULT_CONFIG();
        config.server_port      = streamPort;
        config.max_uri_handlers = 4;
        config.stack_size       = 8192;

        httpd_uri_t stream_uri = {
            .uri      = "/_stream",
            .method   = HTTP_GET,
            .handler  = stream_handler,
            .user_ctx = &streamCtx
        };

        httpd_uri_t capture_uri = {
            .uri      = "/_capture",
            .method   = HTTP_GET,
            .handler  = capture_handler,
            .user_ctx = &streamCtx
        };

        if (httpd_start(&stream_httpd, &config) == ESP_OK) {
            httpd_register_uri_handler(stream_httpd, &stream_uri);
            httpd_register_uri_handler(stream_httpd, &capture_uri);
            return ESP_OK;
        }
        return ESP_FAIL;
    }

    void stopCameraServer() {
        if (stream_httpd) {
            httpd_stop(stream_httpd);
            stream_httpd = nullptr;
        }
    }
};

#endif 

