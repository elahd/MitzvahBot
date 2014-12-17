MitzvahBot
==========

Self lighting menorah for Chanukah. An Arduino/Python project.

My bot Tweets to [@MitzvahBot](https://www.twitter.com/MitzvahBot)

## MitzvahBot:
1. Determines Chanukah dates.
2. Determines candle lighting times based on local sunset times.
3. Says candle lighting prayers via Twitter.
4. Lights candles on a properly configured Arduino.
5. Extinguishes candles after a few hours.

<img src="http://i.imgur.com/wmDW2IH.jpg" height="33%" width="33%" />
<img src="http://i.imgur.com/TlSxgLa.png" height="33%" width="33%" />

[More Images](https://imgur.com/a/Hzz2V)

## To Use:
1. Configure arduino as shown in diagram. Resistors are 330ohm.
2. Load chanukiah.ino to your arduino.
3. Install Python libraries. Use pip on Ubuntu or OSX. Required libraries are pyserial, nap, python-dateutil, and python-twitter.
4. Set appropriate variables in controller.py. You'll need accounts on geonames.org and apps.twitter.com.
5. Connect Arduino to host computer via USB. Run controller.py. (Needs to be run as sudo in Ubuntu for serial access to work.)
6. Wait for Chanukah, or enable debug flag in controller.py before running.
