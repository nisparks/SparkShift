#!/bin/bash
T=/usr/lib/openfoam/openfoam2606/tutorials/incompressible/simpleFoam/motorBike
ls $T $T/system $T/0.orig $T/constant
echo ====== Allrun; cat $T/Allrun
echo ====== turbulenceProperties; sed -n '8,40p' $T/constant/turbulenceProperties
echo ====== transportProperties; sed -n '8,40p' $T/constant/transportProperties
echo ====== fvSolution; sed -n '16,90p' $T/system/fvSolution
echo ====== fvSchemes; sed -n '16,70p' $T/system/fvSchemes
echo ====== surfaceFeatureExtractDict; sed -n '16,60p' $T/system/surfaceFeatureExtractDict
echo ====== 0.orig/U; sed -n '16,60p' $T/0.orig/U
echo ====== include; ls $T/0.orig/include; cat $T/0.orig/include/*
