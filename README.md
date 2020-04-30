# Cytobuf

Experimental protoc plugin to generate cython bindings to generated C++ protobufs.

## Latest Results
```
***** Benchmark Results *****

1 Items per proto:
	*** Compute ***
	Parse:
		json.loads	6,427.37ns
		baseline  	2,880.78ns
		cytobuf   	848.80ns 3.39 X Speedup
		pyrobuf   	5,372.96ns 0.54 X Speedup
	Serialize:
		json.dumps	12,580.07ns
		baseline  	7,573.73ns
		cytobuf   	878.64ns 8.62 X Speedup
		pyrobuf   	4,268.76ns 1.77 X Speedup
	FromJson:
		baseline  	66,977.70ns
		cytobuf   	34,247.67ns 1.96 X Speedup
		pyrobuf   	14,026.50ns 4.78 X Speedup
	ToJson:
		baseline  	70,770.23ns
		cytobuf   	13,612.06ns 5.20 X Speedup
		pyrobuf   	7,446.95ns 9.50 X Speedup
	Iterate:
		json      	275.55ns
		baseline  	1,099.84ns
		cytobuf   	1,136.09ns 0.97 X Speedup
		pyrobuf   	573.13ns 1.92 X Speedup
	Field Access:
		json      	219.11ns
		baseline  	433.34ns
		cytobuf   	187.20ns 2.31 X Speedup
		pyrobuf   	112.36ns 3.86 X Speedup

	*** Memory ***
	baseline Memory for 5k protos:	3.03MB
	cytobuf  Memory for 5k protos:	0.03MB  (98.97% Decrease)
	pyrobuf  Memory for 5k protos:	9.71MB  (220.36% Increase)

10 Items per proto:
	*** Compute ***
	Parse:
		json.loads	25,813.76ns
		baseline  	24,270.09ns
		cytobuf   	5,863.66ns 4.14 X Speedup
		pyrobuf   	45,219.88ns 0.54 X Speedup
	Serialize:
		json.dumps	48,855.20ns
		baseline  	43,501.55ns
		cytobuf   	2,553.76ns 17.03 X Speedup
		pyrobuf   	26,220.14ns 1.66 X Speedup
	FromJson:
		baseline  	987,585.99ns
		cytobuf   	408,490.59ns 2.42 X Speedup
		pyrobuf   	142,621.67ns 6.92 X Speedup
	ToJson:
		baseline  	877,442.93ns
		cytobuf   	65,457.51ns 13.40 X Speedup
		pyrobuf   	85,095.57ns 10.31 X Speedup
	Iterate:
		json      	540.82ns
		baseline  	7,699.36ns
		cytobuf   	4,527.96ns 1.70 X Speedup
		pyrobuf   	666.70ns 11.55 X Speedup
	Field Access:
		json      	248.14ns
		baseline  	424.23ns
		cytobuf   	345.20ns 1.23 X Speedup
		pyrobuf   	225.94ns 1.88 X Speedup

	*** Memory ***
	baseline Memory for 5k protos:	22.17MB
	cytobuf  Memory for 5k protos:	13.29MB  (40.07% Decrease)
	pyrobuf  Memory for 5k protos:	96.11MB  (333.57% Increase)

100 Items per proto:
	*** Compute ***
	Parse:
		json.loads	238,910.61ns
		baseline  	237,223.15ns
		cytobuf   	26,416.82ns 8.98 X Speedup
		pyrobuf   	450,227.60ns 0.53 X Speedup
	Serialize:
		json.dumps	429,471.29ns
		baseline  	544,254.46ns
		cytobuf   	31,322.16ns 17.38 X Speedup
		pyrobuf   	348,879.68ns 1.56 X Speedup
	FromJson:
		baseline  	8,700,561.32ns
		cytobuf   	6,765,228.44ns 1.29 X Speedup
		pyrobuf   	1,180,064.78ns 7.37 X Speedup
	ToJson:
		baseline  	8,036,340.44ns
		cytobuf   	447,607.87ns 17.95 X Speedup
		pyrobuf   	716,667.23ns 11.21 X Speedup
	Iterate:
		json      	1,163.04ns
		baseline  	54,625.13ns
		cytobuf   	19,674.42ns 2.78 X Speedup
		pyrobuf   	856.40ns 63.78 X Speedup
	Field Access:
		json      	115.33ns
		baseline  	485.22ns
		cytobuf   	373.15ns 1.30 X Speedup
		pyrobuf   	212.14ns 2.29 X Speedup

	*** Memory ***
	baseline Memory for 5k protos:	241.04MB
	cytobuf  Memory for 5k protos:	168.13MB  (30.25% Decrease)
	pyrobuf  Memory for 5k protos:	953.23MB  (295.47% Increase)
```