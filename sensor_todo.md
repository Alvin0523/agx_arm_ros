dependence
```
sudo usermod -a -G dialout $USER
sudo udevadm control --reload-rules
sudo udevadm trigger
```
reboot the system

conda env python=3.9
```
pip install acconeer-exptool
```

Use type-c cable
```
ls /dev/ttyACM*
```
run the script
```
python detector.py
```
