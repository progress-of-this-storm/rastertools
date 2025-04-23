# RasterTools for easier raster manipulation in python, mainly built around gdal
# Louie E. Bell, University of Cambridge

# imports
from osgeo import gdal
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
    band = ds.GetRasterBand(1)
    arr = band.ReadAsArray()
    return arr, ds

def write_geotiff(fileName, arr, reference):
    """
    Takes an reference .tif and writes a new.tif file from an array 
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
    out_ds = driver.Create(fileName, arr.shape[1], arr.shape[0], 1, arr_type) # create the file
    out_ds.SetProjection(proj) # use ref dataset to set proj and transform
    out_ds.SetGeoTransform(new_transform)
    band = out_ds.GetRasterBand(1) # write a single band raster
    band.WriteArray(arr) # fill with values
    band.FlushCache()
    band.ComputeStatistics(False)