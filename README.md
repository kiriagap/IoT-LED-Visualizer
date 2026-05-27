# IoT LED Color Music System

## Project Description

This project represents an IoT LED Color Music System using Arduino Nano, WS2812B LED strip, MAX4466 microphone sensor and Flask web application running on Raspberry Pi OS in VirtualBox environment.

The system monitors audio signal values from a real microphone sensor and visualizes them both physically using an addressable RGB LED strip and virtually through a web interface in real time.

The project demonstrates complete IoT architecture:
- sensor data acquisition,
- embedded firmware processing,
- real-time communication,
- web visualization,
- database storage,
- remote internet access.

---

# Measured Physical Quantity

The monitored physical quantity is:
- sound intensity / audio signal level.

The microphone MAX4466 captures analog audio signal values which are processed by Arduino Nano.

---

# Project Purpose

The purpose of the project is:
- real-time sound monitoring,
- LED visualization of audio signal,
- web-based monitoring and control,
- demonstration of IoT technologies,
- demonstration of real hardware communication with web systems.

---

# Hardware Components

## Microcontroller Platform
- Arduino Nano

## Sensor
- MAX4466 microphone module

### Sensor Category
- Category B — analog sensor

The microphone outputs analog voltage values which are processed using the Arduino ADC converter.

## Additional Hardware
- WS2812B addressable RGB LED strip
- USB communication
- Raspberry Pi OS running in VirtualBox
- Windows host system

---

# Software Technologies

## Embedded Firmware
- Arduino IDE
- C/C++

## Server Side
- Python
- Flask
- Flask-SocketIO

## Visualization
- HTML
- CSS
- JavaScript
- Chart.js
- WebSocket communication

## Data Storage
- SQLite database
- CSV file logging

## IoT Access
- ngrok tunnel service

---

# System Architecture

System architecture:

Microphone MAX4466  
↓  
Arduino Nano  
↓  
Serial communication (USB)  
↓  
Flask server (Python)  
↓  
SQLite / CSV logging  
↓  
WebSocket communication  
↓  
Web browser visualization  
↓  
Realtime graph + gauges + controls

---

# Communication Protocol

The system uses:
- Serial communication between Arduino and Flask server
- WebSocket communication between Flask server and web client
- HTTPS tunnel using ngrok

WebSocket was selected because it enables low-latency bidirectional realtime communication.

---

# Transferred Data Format

The system transfers JSON formatted data.

Example:

```json
{
  "value": 512,
  "brightness": 120,
  "mode": "music",
  "timestamp": 1714000000
}
