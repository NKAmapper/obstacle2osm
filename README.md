# obstacle2osm
Extracts aviation obstacles from Kartverket to OSM

### Usage

<code>python obstacle2osm.py [county]</code>

* Supply a two digit <code>county</code> code 01, 02 etc.
* A county code of <code>00</code> will give all of Norway (approx. 5 min runtime)
* Results are presented as an OSM file named according to the respective county code: *Luftfartshinder_Vestfold.osm*
* Uses the local library [utm.py](https://github.com/osmno/obstacle2osm/blob/master/utm.py)
  
### Notes

* Please include the unique identifier <code>ref:hinder</code> for further updates
* Additional info: [Aviation Obstacle Import Norway](https://wiki.openstreetmap.org/wiki/Import/Catalogue/Aviation_Obstacle_Import_Norway)
* A generated OSM file for Norway is available [here](https://drive.google.com/drive/folders/1Dln7YFmkO52R_VCYZyFgaqX0GMoYiqQR?usp=sharing)
* Thanks to [Nenad Uzunovic](https://nenadsprojects.wordpress.com/2012/12/27/latitude-and-longitude-utm-conversion/) for the library converting between UTM and WGS84
