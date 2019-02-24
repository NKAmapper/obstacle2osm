# obstacle2osm
Extracts aviation obstacles from Kartverket to OSM

### Usage

<code>python obstacle2osm.py [county]</code>

* Use two digit <code>county</code> code 01, 02 etc.
* County code <code>00</code> will give all of Norway (approx. 5 min runtime)
* Produces OSM file with name like *Luftfartshinder_Vestfold.osm*
* Code uses local library [utm.py](https://github.com/osmno/obstacle2osm/blob/master/utm.py)
  
### Notes

* Please include the unique identifier <code>ref:hinder</code> for later updates
* Further information: [Aviation Obstacle Import Norway](https://wiki.openstreetmap.org/wiki/Import/Catalogue/Aviation_Obstacle_Import_Norway)
* Generated OSM file for Norway is available [here](https://drive.google.com/drive/folders/1Dln7YFmkO52R_VCYZyFgaqX0GMoYiqQR?usp=sharing)
* Thanks to [Nenad Uzunovic](https://nenadsprojects.wordpress.com/2012/12/27/latitude-and-longitude-utm-conversion/) for library to convert between UTM and WGS84
