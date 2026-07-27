# Sequence — AWPTCM-T33234

1. Configure switch port1.0.1: speed auto, duplex auto, polarity auto
   verify: CLI accepts commands without error
2. Configure partner port: speed auto, duplex auto, polarity auto
   verify: CLI accepts commands without error
3. Run show interface port1.0.1
   verify: Output shows auto polarity, auto duplex/speed, link down
4. Prompt operator to insert supported pluggable into port1.0.1
   verify: Wait for link up; show interface port1.0.1 shows link up, resolved polarity, negotiated speed/duplex
5. Connect straight-through cable between port1.0.1 and partner
   verify: show interface port1.0.1 shows link up, polarity resolved correctly
6. Replace with crossover cable
   verify: show interface port1.0.1 shows link up, polarity resolved correctly
7. Configure partner port: polarity mdi
   verify: CLI accepts command
8. Connect straight-through cable
   verify: show interface port1.0.1 shows link up
9. Configure partner port: polarity mdix
   verify: CLI accepts command
10. Connect crossover cable
   verify: show interface port1.0.1 shows link up
11. Configure partner port: polarity mdi
   verify: CLI accepts command
12. Connect crossover cable
   verify: show interface port1.0.1 shows link down
13. Configure partner port: polarity mdix
   verify: CLI accepts command
14. Connect straight-through cable
   verify: show interface port1.0.1 shows link down
15. Run show interface port1.0.1
   verify: Output contains current polarity <mdi/mdix>, current duplex <full/half>, current speed <value>
16. Poll show interface port1.0.1 status 5 times at 1s intervals
   verify: State remains connected/consistent across all polls, no link flaps
17. Prompt operator to remove pluggable from port1.0.1
   verify: show interface port1.0.1 shows link down
18. Prompt operator to insert pluggable back into port1.0.1
   verify: show interface port1.0.1 shows link up, polarity resolved
19. Run ecofriendly lpi
   verify: show ecofriendly output shows Configured column as lpi for port1.0.1
20. Run no ecofriendly lpi
   verify: show ecofriendly output shows Configured column as off for port1.0.1; show interface port1.0.1 shows link remains up
