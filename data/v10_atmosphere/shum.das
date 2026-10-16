Attributes {
    level {
        String units "millibar";
        String long_name "Level";
        String positive "down";
        Int16 GRIB_id 100;
        String GRIB_name "hPa";
        Float32 actual_range 1000.0, 300.0;
        String axis "Z";
    }
    lon {
        String units "degrees_east";
        String long_name "Longitude";
        Float32 actual_range 0.0, 357.5;
        String standard_name "longitude";
        String axis "X";
    }
    lat {
        String units "degrees_north";
        Float32 actual_range 90.0, -90.0;
        String long_name "Latitude";
        String standard_name "latitude";
        String axis "Y";
    }
    time {
        String long_name "Time";
        String delta_t "0000-01-00 00:00:00";
        String avg_period "0030-00-00 00:00:00";
        String prev_avg_period "0000-01-00 00:00:00";
        String standard_name "time";
        String axis "T";
        String climatology "climatology_bounds";
        String climo_period "1981/01/01 - 2010/12/31";
        String interpreted_actual_range "0001/01/01 00:00:00 - 0001/12/01 00:00:00";
        String units "days since 1800-01-01 00:00:0.0";
        Float64 actual_range -657073.0, -656739.0;
    }
    shum {
        String long_name "Monthly Long Term Mean of Specific Humidity";
        String units "grams/kg";
        Float32 add_offset 0.0;
        Float32 scale_factor 1.0;
        Float32 missing_value -9.96921E36;
        Int16 precision 3;
        Int16 least_significant_digit 0;
        String var_desc "Specific Humidity";
        String level_desc "Pressure Levels";
        String statistic "Long Term Mean";
        String parent_stat "Mean";
        Float32 valid_range -0.09999999, 100.43;
        Float32 actual_range -6.359769E-7, 35.805397;
        String dataset "NCEP Reanalysis Derived Products";
        UInt32 _ChunkSizes 1, 1, 73, 144;
    }
    climatology_bounds {
        String long_name "Climate Time Boundaries";
        String units "hours since 1-1-1 00:00:0.0";
    }
    valid_yr_count {
        Int16 missing_value 32767;
        Float32 add_offset 0.0;
        Float32 scale_factor 1.0;
        String long_name "count of non-missing values used in mean";
        UInt32 _ChunkSizes 1, 1, 73, 144;
    }
    NC_GLOBAL {
        String description "Data is from NMC initialized reanalysis
(4x/day).  It consists of most variables interpolated to
pressure surfaces from model (sigma) surfaces.";
        String platform "Model";
        String Conventions "COARDS";
        String not_missing_threshold_percent "minimum 3% values input to have non-missing output value";
        String history "Created 2011/07/12 by doMonthLTM
Converted to chunked, deflated non-packed NetCDF4 2014/09";
        String title "monthly ltm shum from the NCEP Reanalysis";
        String dataset_title "NCEP-NCAR Reanalysis 1";
        String References "http://www.psl.noaa.gov/data/gridded/data.ncep.reanalysis.derived.html";
        String _NCProperties "version=2,netcdf=4.6.3,hdf5=1.10.5";
    }
}
