/*
  The MIT License

  Copyright (c) 2016 Thomas Sarlandie thomas@sarlandie.net

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in
  all copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
  THE SOFTWARE.
*/
#include "ADCTask.h"
#include "KBoxDebug.h"
#include "../drivers/board.h"

#include <NMEA2000.h>
#include <N2kMessages.h>

void ADCTask::loop() {
  int supply_adc = adc.analogRead(supply_analog, ADC_0);
  int bat1_adc = adc.analogRead(bat1_analog, ADC_0);
  int bat2_adc = adc.analogRead(bat2_analog, ADC_0);
  //int bat3_adc = adc.analogRead(bat3_analog, ADC_0); //deactivated while bat3 input is used for rudderSensor input
    
  //DEBUG("ADC - Supply: %sV Bat1: %sV Bat2: %sV Bat3: %sV", 
      //String(supply, 2).c_str(), String(bat1, 2).c_str(), String(bat2, 2).c_str(), String(bat3, 2).c_str());

  VoltageMeasurement m1(0, "house", bat1);
  VoltageMeasurement m2(1, "starter", bat2);
  VoltageMeasurement mSupply(3, "supply", supply);
  VoltageMeasurement m3(4, "bat3", bat3);

  sendMessage(m1);
  sendMessage(m2);
  sendMessage(m3);
  sendMessage(mSupply);
}
