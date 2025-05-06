# RasterTools for easier raster manipulation in python, mainly built around gdal
# Louie E. Bell, University of Cambridge

# imports
from osgeo import gdal, ogr
import numpy as np

def read_reference_tiff(refPath):
    """
    Reads reference geoTiff and returns source transform, projection and metadata for further processing.

    Input : `.tif` file
    Outputs:
        - `ref_transform`
        - `ref_projection`
        - `reference`
    
    Louie E. Bell, University of Cambridge
    """
    reference = gdal.Open(refPath) # open reference .tif
    ref_transform = reference.GetGeoTransform() # get transform
    ref_projection = reference.GetProjection() # get projection
    return ref_transform, ref_projection, reference

def read_geotiff(fileName):
    """Reads .tif filepath to an array and a gdal dataset object """
    ds = gdal.Open(fileName)
    count = ds.RasterCount
    if count > 1:
        stack = np.empty((ds.RasterYSize, ds.RasterXSize, count), dtype = np.uint32)
        for band in range(count):
            rband = ds.GetRasterBand(band+1)
            arr = rband.ReadAsArray()
            stack[:, :, band] = arr
        return stack, ds
    else:
        band = ds.GetRasterBand(1)
        arr = band.ReadAsArray()
        return arr, ds

def write_geotiff(arr, folder, reference, name):
    """
    Takes an reference .tif and writes a new.tif file from an array
    Inputs:
        - `arr`, array-type
        - `filePath`, filePath to write to including filename ending in .tif
        - `reference`, rastertools reference object from `read_reference_tiff`

    Outputs:
        - single/multiple .tif files dependent on axis 2 length of array
    """
    if arr.dtype == np.float32: # parse array data type
        arr_type = gdal.GDT_Float32
    else:
        arr_type = gdal.GDT_Int32

    trans, proj, refData = reference
    # Compute new pixel size
    ref_rows, ref_cols = refData.RasterYSize, refData.RasterXSize
    arr_rows = arr.shape[0]
    arr_cols = arr.shape[1]

    x_res = trans[1] * (ref_cols / arr_cols) # multiply the reference pixel width by the column scalar
    y_res = trans[5] * (ref_rows / arr_rows) # multiply the reference pixel height by the row scalar

    # Shift the origin by half a pixel
    new_origin_x = trans[0] + 0.5 * (trans[1] - x_res)
    new_origin_y = trans[3] + 0.5 * (trans[5] - y_res)
    
    new_transform = (
        new_origin_x,
        x_res,
        trans[2],
        new_origin_y,
        trans[4],
        y_res
    )

    driver = gdal.GetDriverByName("GTiff") # set file driver

    if len(arr.shape) > 2: # if a n-dim array
        for rband in range(arr.shape[2]): # loop over bands and write each to .tif 
            out_ds = driver.Create(f'{folder}/{name}_{rband}.tif', arr.shape[1], arr.shape[0], 1, arr_type) # create the file
            out_ds.SetProjection(proj) # use ref dataset to set proj and transform
            out_ds.SetGeoTransform(new_transform)
            band = out_ds.GetRasterBand(1) # write a single band raster
            band.WriteArray(arr[:, :, rband]) # fill with values
            band.FlushCache()
            band.ComputeStatistics(False)
    else:
        out_ds = driver.Create(f'{folder}/{name}.tif', arr.shape[1], arr.shape[0], 1, arr_type) # create the file
        out_ds.SetProjection(proj) # use ref dataset to set proj and transform
        out_ds.SetGeoTransform(new_transform)
        band = out_ds.GetRasterBand(1) # write a single band raster
        band.WriteArray(arr) # fill with values
        band.FlushCache()
        band.ComputeStatistics(False)  

def mask_raster_with_shapefile(raster_path, shapefile_path, output_path, nodata_value=np.nan):
    """
    Masks a raster using a shapefile by setting pixels inside the shapefile to a nodata value.
    """
    # Open raster
    raster_ds = gdal.Open(raster_path, gdal.GA_Update)
    band = raster_ds.GetRasterBand(1)
    raster_array = band.ReadAsArray()
    
    # Create an empty mask with the same size as the raster
    mask_ds = gdal.GetDriverByName('MEM').Create('', raster_ds.RasterXSize, raster_ds.RasterYSize, 1, gdal.GDT_Byte)
    mask_ds.SetGeoTransform(raster_ds.GetGeoTransform())
    mask_ds.SetProjection(raster_ds.GetProjection())

    # Open shapefile
    shp_ds = ogr.Open(shapefile_path)
    shp_layer = shp_ds.GetLayer()

    # Rasterize shapefile into the mask dataset
    gdal.RasterizeLayer(mask_ds, [1], shp_layer, burn_values=[1])

    # Read the mask as an array
    mask_array = mask_ds.GetRasterBand(1).ReadAsArray()

    # Apply the mask: Set pixels inside the shapefile to the nodata value
    raster_array = raster_array.astype(np.float32) 
    raster_array[mask_array == 1] = nodata_value

    # Save the masked raster
    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(output_path, raster_ds.RasterXSize, raster_ds.RasterYSize, 1, gdal.GDT_Float32)
    out_ds.SetGeoTransform(raster_ds.GetGeoTransform())
    out_ds.SetProjection(raster_ds.GetProjection())

    out_band = out_ds.GetRasterBand(1)
    out_band.WriteArray(raster_array)
    out_band.SetNoDataValue(nodata_value)
    out_band.FlushCache()

    # Cleanup
    raster_ds = None
    mask_ds = None
    shp_ds = None
    out_ds = None
    print(f"Masked raster saved to {output_path}")