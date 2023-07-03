mpremote fs mkdir :/system
mpremote resume fs cp system/*.py :/system/
mpremote resume fs mkdir :/programs
mpremote resume fs cp programs/*.py :/programs/
mpremote resume fs cp *.py :
mpremote resume fs touch :/bma423.fw
if [ $? -eq 0 ]; then
    echo "bma fw already copied"
else
    mpremote resume fs cp *.fw :
fi

mpremote resume fs ls :/system/fonts
if [ $? -eq 0 ]; then
    echo "fonts already copied"
else
    mpremote resume fs mkdir :/system/fonts
    mpremote resume fs cp system/fonts/*.py :/system/fonts/
fi
