# Wifi_Signal_locator

A Python-based desktop application that scans nearby WiFi access points and estimates the device's geographical location using WiFi network information. It features a dark-themed Tkinter interface with an animated radar, signal-strength indicators, network filtering, location results, and Google Maps integration.

The application can also use IP-based geolocation as a fallback when WiFi-based geolocation fails.

## Features

- **Cross-platform WiFi scanning**
  - Windows: `netsh`
  - Linux: `nmcli` or `iwlist`
  - macOS: `airport -s`
- **WiFi network discovery** — identifies nearby access points and displays their available details.
- **Signal-strength analysis** — displays signal strength in dBm and provides visual signal indicators.
- **Network information** — shows SSID, BSSID, channel, and security information when available.
- **WiFi-based geolocation** — submits nearby access-point information to the configured Mozilla Location Services endpoint.
- **IP-based fallback** — attempts IP geolocation if WiFi-based location lookup fails.
- **Animated radar interface** — provides a visual scanning animation.
- **Network filtering and sorting** — helps find specific access points in the results table.
- **Location results** — displays latitude, longitude, estimated accuracy, and timestamp.
- **Google Maps integration** — opens the estimated coordinates in a browser.
- **Copy coordinates** — copies the location coordinates to the clipboard.
- **Background processing** — performs scans and location requests in worker threads to keep the interface responsive.

## Technologies Used

- Python 3.8+
- Tkinter and ttk
- Python standard-library modules:
  - `subprocess`
  - `threading`
  - `urllib`
  - `json`
  - `platform`
  - `re`
  - `math`
  - `datetime`
- Mozilla Location Services endpoint configured in the source
- ipify and ip-api.com for the documented IP lookup workflow

## Requirements

- Python 3.8 or later
- A WiFi adapter capable of scanning nearby networks
- Internet access for online geolocation requests
- Appropriate operating-system permissions and WiFi scanning utilities

### Platform requirements

| Operating system | Scanning method | Requirements |
|---|---|---|
| Windows | `netsh wlan` | Enabled WiFi adapter |
| Linux | `nmcli` or `iwlist` | NetworkManager or wireless-tools, as applicable |
| macOS | `airport -s` | Availability of the legacy `airport` utility; compatibility varies by macOS version |

## Installation

### 1. Clone the repository

Replace the example URL with your actual GitHub repository URL.

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
cd YOUR-REPOSITORY
```

### 2. Verify Python

```bash
python --version
```

On Linux or macOS, you may need:

```bash
python3 --version
```

### 3. Install Linux scanning utilities if needed

For NetworkManager:

```bash
sudo apt update
sudo apt install network-manager
```

For systems using `iwlist`, install the relevant wireless-tools package if available:

```bash
sudo apt install wireless-tools
```

The required utility depends on your Linux distribution and WiFi configuration.

### 4. Run the application

Save the source file as `wifi_locator.py`, then execute:

```bash
python wifi_locator.py
```

On Linux or macOS:

```bash
python3 wifi_locator.py
```

No third-party Python packages are required by the supplied source code.

## How to Use

1. Launch the application.
2. Click **Scan WiFi Networks** to discover nearby access points.
3. Review the detected networks in the table.
4. Examine each network's SSID, BSSID, signal strength, channel, and security information.
5. Use the search field to filter the displayed network list.
6. Click **Locate Me** after a successful scan.
7. The application attempts WiFi-based geolocation using the configured service.
8. If that request fails, the application attempts IP-based geolocation.
9. Review the estimated latitude, longitude, accuracy, and timestamp.
10. Click **Open in Google Maps** to view the estimated coordinates.
11. Click **Copy coordinates** to copy the latitude and longitude.

## How It Works

```text
Start Application
        |
        v
Scan Nearby WiFi Networks
        |
        v
Collect Available Access-Point Data
(SSID, BSSID, Signal, Channel)
        |
        v
Submit WiFi Data to Configured
Geolocation Service
        |
        +------ Success ------> Display Estimated Location
        |
        +------ Failure ------> Attempt IP-Based Geolocation
                                      |
                                      v
                              Display Fallback Result
        |
        v
Open Coordinates in Google Maps
or Copy Coordinates
```

## Geolocation Services

### WiFi-based geolocation

The source submits nearby access-point BSSIDs, signal strengths, and channel values to the configured Mozilla Location Services endpoint.

The response is used to obtain an estimated latitude, longitude, and accuracy value.

The endpoint configured in the supplied source is:

`https://location.services.mozilla.com/v1/geolocate?key=test`

**Note:** The application depends on the availability and acceptance of this endpoint and its configured key. Verify that the service is operational before relying on WiFi-based geolocation.

### IP-based fallback

When WiFi geolocation fails, the source attempts to retrieve approximate coordinates and network information using:

`http://ip-api.com/json/?fields=lat,lon,city,country,query`

The fallback result uses a nominal accuracy value of 5,000 metres in the application. This is an application-defined estimate, not a guarantee of actual location accuracy.

## Privacy and Security

- The application reads nearby WiFi access-point information through the local wireless adapter.
- WiFi geolocation requests transmit BSSID and signal information to the configured external service.
- IP-based fallback requests send network requests to a third-party service.
- The fallback endpoint uses HTTP rather than HTTPS, so its request is not protected by transport encryption.
- Location results may be inaccurate, unavailable, or affected by network conditions.
- Only scan WiFi networks on devices and systems you are authorised to use.
- Review the current privacy policies and availability of external services before using this tool.

## Troubleshooting

### No WiFi networks found

- Confirm that the WiFi adapter is enabled.
- Ensure WiFi scanning is supported by the operating system and adapter.
- On Linux, verify that `nmcli` or `iwlist` is installed and usable.
- Check whether system permissions restrict network scanning.

### WiFi scan fails on Linux

Try installing NetworkManager:

```bash
sudo apt install network-manager
```

Alternatively, install wireless-tools if your system supports the `iwlist` method. Some environments may require elevated permissions.

### Location lookup fails

- Verify your internet connection.
- Check whether the configured geolocation endpoint is available.
- Check for API errors, endpoint restrictions, or service changes.
- Remember that IP fallback also requires an accessible external service.

### Google Maps does not open

Ensure that a default web browser is installed and configured on your system.

### Location is inaccurate

WiFi and IP geolocation provide estimates. Results depend on available access points, service coverage, network routing, and the geolocation provider's data.

## Project Structure

```text
YOUR-REPOSITORY/
├── wifi_locator.py
├── README.md
└── .gitignore
```

## Future Enhancements

- Export scan results to CSV or JSON.
- Add a persistent history and location comparison view.
- Support additional modern WiFi scanning interfaces.
- Add configurable geolocation providers.
- Improve validation and error handling for API responses.
- Provide clearer privacy controls before submitting WiFi information.

These are suggested improvements and are not claimed as implemented features.

## Contributing

Contributions and suggestions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Implement and test your changes.
4. Commit your changes with a descriptive message.
5. Submit a pull request.

## License

No license is specified in the supplied source code. Add a `LICENSE` file to your repository if you intend to define permissions for reuse, modification, and distribution.

## Disclaimer

This project is intended for educational, diagnostic, and authorised location-estimation purposes. It does not use GPS, and it cannot guarantee exact physical location. Use the results as approximate information rather than as the sole basis for safety-critical or security-critical decisions.
