# dataset_profile
## Información general

La base de muestra corresponde al mes de enero 2025 `yellow_tripdata_2025-01.parquet` la cual tiene documentación clara y completa del propietario de la información.

* El dataset principal tiene 20 columnas y 3,475,226 filas
* El dataset secundario tiene 7 columnas y 263 filas
* El dataset principal utiliza un espacio de memoria: 616.31 MB
* El dataset secundario utiliza un espacio de memoria: 1.61 MB
* Para las fechas de `tpep_pickup_datetime` y `tpep_dropoff_datetime` se debe realizar una limpieza de rango correspondiente a 2025.
    * Rango de fechas en los datos de `tpep_pickup_datetime`
        - Mínima: 2024-12-31 20:47:55
        - Máxima: 2025-02-01 00:00:44
    * Rango de fechas en los datos de `tpep_dropoff_datetime`
        - Mínima: 2024-12-18 07:52:40
        - Máxima: 2025-02-01 23:44:11
* Si hay campos con valores NaN y None en un estimado del 3.89%

## Diccionario de datos

### Dataset principal
#### Yellow Taxi Trip Records

|No.|Columna|Descripción|Tipo de dato|Ejemplo de valor|
|---|-------|-----------|------------|----------------|
|1|`VendorID`|Un código que indica el proveedor TPEP que proporcionó el registro.|int32/Number|1 = Creative Mobile Technologies, LLC <br>2 = Curb Mobility, LLC <br>6 = Myle Technologies Inc <br>7 = Helix|
|2|`tpep_pickup_datetime`|La fecha y la hora en que se activó el medidor.|datetime64[us]/Floating Timestamp|2025-01-31 23:01:48 <br>2025-01-31 23:50:29|
|3|`tpep_dropoff_datetime`|La fecha y hora en que se desconectó el medidor.|datetime64[us]/Floating Timestamp|2025-01-31 23:16:29 <br>2025-02-01 00:17:27|
|4|`passenger_count`|El número de pasajeros en el vehículo.|float64/Number|0.0 <br>3.0 <br>NaN|
|5|`trip_distance`|La distancia de viaje transcurrida en millas reportada por el taxímetro.|float64/Number|3.35 <br>8.73|
|6|`RatecodeID`|El código de tarifa final vigente al final del viaje.|float64/Number|1.0= Tarifa estándar <br>2.0= JFK <br>3.0= Newark <br>4.0= Nassau o Westchester <br>5.0= Tarifa negociada <br>6.0= Viaje en grupo <br>99.0= Nulo/desconocido <br>NaN|
|7|`store_and_fwd_flag`|Esta bandera indica si el registro del viaje se mantuvo en la memoria del vehículo antes de enviarlo al proveedor, también conocido como “almacenar y reenviar”, porque el vehículo no tenía conexión con el servidor.|object/Text|Y = viaje de almacenamiento y reenvío <br>N = no es un viaje de almacenamiento y reenvío <br>None|
|8|`PULocationID`|Zona de taxi TLC en la que se activó el taxímetro|int32/Number|79 <br>161|
|9|`DOLocationID`|Zona de taxi TLC en la que el taxímetro estaba desactivado|int32/Number|237 <br>116|
|10|`payment_type`|Un código numérico que indica cómo pagó el pasajero por el viaje.|int64/Number|0= Viaje con tarifa flexible <br>1= Tarjeta de crédito <br>2= Efectivo <br>3= Sin cargo <br>4= Disputa <br>5= Desconocido <br>6= Viaje anulado|
|11|`fare_amount`|La tarifa por tiempo y distancia calculada por el medidor. Para obtener información adicional sobre las siguientes columnas, consulte https://www.nyc.gov/site/tlc/passengers/taxi-fare.page|float64/Number|15.85 <br>28.14|
|12|`extra`|Extras y recargos varios.|float64/Number|0.0 <br>0.0|
|13|`mta_tax`|Impuesto que se activa automáticamente según la tarifa medida en uso.|float64/Number|0.5|
|14|`tip_amount`|Cantidad de propina: Este campo se completa automáticamente para propinas con tarjeta de crédito. Las propinas en efectivo no están incluidas.|float64/Number|0.0|
|15|`tolls_amount`|Cantidad total de todos los peajes pagados en el viaje.|float64/Number|0.0|
|16|`improvement_surcharge`|Recargo por mejoras aplicado a los viajes desde el inicio de la carrera. El recargo por mejoras comenzó a cobrarse en 2015.|float64/Number|1.0|
|17|`total_amount`|El monto total cobrado a los pasajeros. No incluye propinas en efectivo.|float64/Number|20.60 <br>32.89|
|18|`congestion_surcharge`|Monto total recaudado en el viaje por el recargo de congestión del estado de Nueva York.|float64/Number|2.5 <br>NaN|
|19|`Airport_fee`|Solo para recoger en los aeropuertos LaGuardia y John F. Kennedy.|float64/Number|0.00 <br>1.75 <br>NaN|
|20|`cbd_congestion_fee`|Cargo por viaje para la Zona de Alivio de Congestión de la MTA a partir del 5 de enero de 2025.|float64/Number|0.75 <br>0.00|

Fuente: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

### Dataset secundario
#### Tabla de zonas

|No.|Columna|Descripción|Tipo de dato|Ejemplo de valor|
|---|-------|-----------|------------|----------------|
|1|OBJECTID|Identificador único interno del sistema. Es un número secuencial generado automáticamente para cada registro (ID de feature interno).|int32/Number|1 <br>2|
|2|Shape_Leng|Longitud del perímetro del polígono que representa la zona de taxi, medida en unidades del sistema de coordenadas del mapa.|object/Float|0.11635745319 <br>0.43346966679|
|3|Shape_Area|Área del polígono de la zona de taxi, medida en unidades cuadradas del sistema de coordenadas del mapa.|object/Float|0.00078230679 <br>0.00486634038|
|4|zone|Nombre de la zona de taxi. Corresponde a un barrio o área específica de NYC (ej: "Midtown", "JFK Airport", "Upper East Side").|object/Text|Newark Airport <br>Jamaica Bay|
|5|LocationID|Identificador único numérico de la zona. Este es el campo que vincula directamente con los datos de los viajes (PULocationID y DOLocationID).|int32/Number|1 <br>2|
|6|borough|Distrito de Nueva York donde se ubica la zona. Valores posibles: Manhattan, Brooklyn, Queens, Bronx, Staten Island.|object/Text|EWR <br>Queens|
|7|geometry|Objeto geoespacial que define el polígono (la forma y límites geográficos) de la zona en el mapa. Este campo permite visualizar y hacer análisis espacial.|object/Geometry|b'\x01\x03\x00\x00\x00\x01\x00\x00\x00\xe8\x00... <br>b'\x01\x06\x00\x00\x00!\x00\x00\x00\x01\x03\x0...|

Fuente: https://source.coop/cholmes/nyc-taxi-zones
