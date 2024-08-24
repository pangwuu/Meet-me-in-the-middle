Website

## Backend

1. Figure out how APIs work
2. Convert 

### High level pseudocode

1. Get both locations
2. Convert both locations to coordinates A and B (geocode)
3. Get 3 (or some other number) points which divide A and B like this using cartesian coordinates
A----M----B
A--M------B
A------M--B
4. Use the distanceMatrix API to find the travel distances between AM1, AM2, AM3... BM1, BM2, and BM3
    4a. This will account for different modes of transport (so if A is driving and B is PTing then it won't 
    be an issue)
    4b. We pick the point where M = |AM1 - BM1| is minimised, which will form the point which we
    consider the middle point for them
5. Pick 10 locations within a 100m radius of M which can form where the people can meet up.
    Use the places_nearby API for this
    5a. If 10 locations don't exist, try with a larger search radius (500m, 1km, 2km etc etc)
    5b. This can be mixed with preferences (such as if they wanted to meet for coffee, only include cafes)
