Attempt to connect to a Meta Ray-Ban.

Currently doesn't do anything other than attempt to make a connection.

Only tested with SimStella on Android Emulator so far, not with the emulated Meta Ray-Ban firmware or a real Meta Ray-Ban.

```
./gen_proto.sh
```

```
$ bumble-scan --device-config device.json android-netsim
<<< connecting to HCI...
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1768965861.684181 104358983 fork_posix.cc:71] Other threads are currently calling into gRPC, skipping fork() handlers
I0000 00:00:1768965861.692980 104358983 fork_posix.cc:71] Other threads are currently calling into gRPC, skipping fork() handlers
<<< connected
>>> 69:55:EA:4D:79:5E [RANDOM](resolvable):
  RSSI:  20 ██████████████████████████████
  [Flags]: LE_GENERAL_DISCOVERABLE_MODE
  [Complete Local Name]: 'sdk_gphone64_arm64'
  [Manufacturer Specific Data]: company='Meta Platforms, Inc.', data=030101

^C
Aborted!
$ bumble-pair device.json android-netsim "69:55:EA:4D:79:5E"
<<< connecting to HCI...
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1768965936.353620 104360235 fork_posix.cc:71] Other threads are currently calling into gRPC, skipping fork() handlers
I0000 00:00:1768965936.360931 104360235 fork_posix.cc:71] Other threads are currently calling into gRPC, skipping fork() handlers
<<< connected
=== Connecting to 69:55:EA:4D:79:5E...
<<< Connection: Connection(transport=LE, handle=0x0200, role=CENTRAL, self_address=F3:A8:E3:23:C6:EA, self_resolvable_address=None, peer_address=69:55:EA:4D:79:5E, peer_resolvable_address=None)
***-----------------------------------
*** Pairing starting
***-----------------------------------
###-----------------------------------
### Pairing with sdk_gphone64_arm64 [69:55:EA:4D:79:5E]
###-----------------------------------
>>> Does the other device display 787630? yes
@@@-----------------------------------
@@@ Connection is encrypted
@@@-----------------------------------
***-----------------------------------
*** Paired! (peer identity=BB:BB:BB:00:00:02/P)
*** address_type: 0
*** ltk:
***   value: 22b014e745ea435c190721bc0d918d52
***   authenticated: True
*** irk:
***   value: c7c63640bb80dfa24fd6cf9026c85032
***   authenticated: True
***-----------------------------------
^C
Aborted!
$ python3 starcruiser.py 
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1768966235.965408 104365412 fork_posix.cc:71] Other threads are currently calling into gRPC, skipping fork() handlers
I0000 00:00:1768966235.970663 104365412 fork_posix.cc:71] Other threads are currently calling into gRPC, skipping fork() handlers
Service(handle=0x0086, uuid=UUID-16:FD5F) Characteristic(handle=0x0088, uuid=05ACBE9F-6F61-4CA9-80BF-C8BBB52991C0, READ) 128
CoC(64->71, State=CONNECTED, PSM=128, MTU=2048/65535, MPS=2048/27, credits=65535/256)
```

If you need to re-pair, can use the public address instead:

```
bumble-pair device.json android-netsim "BB:BB:BB:00:00:02/P@"
```