# Meet me in the middle
## Overview
**Meet me in the middle** is a web application that helps two people find a convenient meeting point between their respective locations, optimizing travel times to ensure both individuals have an equal journey duration. By leveraging the Google Maps API, this application not only computes the optimal midpoint but also allows users to specify the type of location they want to visit—be it a café, park, restaurant, or any other place of interest.

Whether you're meeting a friend halfway or planning a rendezvous point for business, **Meet me in the middle** makes it easier than ever to coordinate the perfect location.

## Features
- Equal Travel Time Calculation: Enter two sets of coordinates and select two modes of travel (e.g., walking, driving). The application calculates a midpoint that takes both users an equal amount of time to reach.
- Location Type Selection: Choose the type of venue you're interested in visiting near the calculated midpoint—cafes, libraries, restaurants, etc.
Interactive Map Integration: Uses Google Maps to visually display the midpoint and search results, providing a seamless and intuitive user experience.
- User-Friendly Interface: A clean and minimalistic design, powered by HTML, CSS, and a touch of JavaScript for interactivity.
- Data Persistence with SQLite: Store user preferences and past searches to enhance the user experience upon return visits.
Technologies Used
- Python with Flask: Backend server and application logic.
- SQLite3: Lightweight database for managing user data and search history.
- HTML/CSS/JavaScript: Frontend technologies for crafting a responsive and interactive user interface.
- Google Maps API: Heavily utilized for distance calculations, mapping, and finding locations of interest.
- Responsive Design: Ensures the application is accessible and functional across all devices, including desktops, tablets, and smartphones.

## Technologies Used
- Python with Flask: Backend server and application logic.
- SQLite3: Lightweight database for managing user data and search history.
- HTML/CSS/JavaScript: Frontend technologies for crafting a responsive and interactive user interface.
- Google Maps API: Heavily utilized for distance calculations, mapping, and finding locations of interest.
- Responsive Design: Ensures the application is accessible and functional across all devices, including desktops, tablets, and smartphones.

## Installation and Setup
1. To run the Midpoint Finder web application locally, follow these steps:
```
git clone https://github.com/your-username/midpoint-finder.git
cd midpoint-finder
```
2. Install Required Dependencies: Ensure you have Python installed (preferably version 3.7 or higher). Install Flask and other dependencies via pip.
```
pip install flask
pip install flask sqlalchemy
pip install googlemaps
pip install geopy
pip install urllib
```
3. Set Up Your Google Maps API Key: Obtain an API key from the [Google Cloud Platform](https://cloud.google.com/free/?utm_source=google&utm_medium=cpc&utm_campaign=japac-AU-all-en-dr-BKWS-all-core-trial-EXA-dr-1605216&utm_content=text-ad-none-none-DEV_c-CRE_602320994293-ADGP_Hybrid+%7C+BKWS+-+EXA+%7C+Txt+-GCP-General-core+brand-main-KWID_43700071544383179-kwd-26415313501&userloc_9071810-network_g&utm_term=KW_google%20cloud%20platform&gad_source=1&gclid=CjwKCAjwiaa2BhAiEiwAQBgyHh7e9xYKSlD8UYuoCrnyRubMfRLATsSG0oZMLvQ00TvGQk2-vggLBhoCP30QAvD_BwE&gclsrc=aw.ds).
Set the GOOG_API_KEY environment variable to your Google Maps API Key
4. Initialize the database:
```
python init_db.py
```
5. Run the application
```
python3 app.py
```

## Usage
1. Enter Coordinates: Input the coordinates of two locations you wish to find a midpoint for.
2. Select Travel Modes: Choose the mode of travel for each user (e.g., walking, driving).
3. Specify Location Type: Enter the type of venue you wish to find near the midpoint (e.g., cafes, restaurants).
4. View Results: The application displays the calculated midpoint on an interactive Google Map, along with the nearest places of interest.

## Future Enhancements
1. Enhanced Recommendation System: Integrate machine learning algorithms to recommend venues based on user preferences and past behavior.
2. Real-Time Traffic Data: Incorporate real-time traffic updates to provide more accurate travel time estimations.
3. Multi-User Support: Extend functionality to support group meetups with more than two people.

## Contributing
Contributions are welcome! If you have ideas for improvements or new features, feel free to fork the repository and submit a pull request.

## License
This project is licensed under the Apache 2.0 License - see the LICENSE file for details.