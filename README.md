# obstacle2osm
Extracts aviation obstacles from Kartverket to OSM.

### Usage

<code>python obstacle2osm.py \<county\> [-line]</code>

* Provide <code>county</code> name, or _Norway_ for whole country.
* Add <code>-line</code> argument to output power lines only.
* Result is saved as geojson file.
* Dependency on [gml2osm](https://github.com/NKAmapper/gml2osm) (load gml2osm.py into same folder).
  
### Notes

* Please include the unique identifier <code>ref:hinder</code> when uploading to OSM for later updates.
* Additional info: [Aviation Obstacle Import Norway](https://wiki.openstreetmap.org/wiki/Import/Catalogue/Aviation_Obstacle_Import_Norway).
* Generated files for Norway are available [here](https://drive.google.com/drive/folders/1Dln7YFmkO52R_VCYZyFgaqX0GMoYiqQR?usp=sharing).
