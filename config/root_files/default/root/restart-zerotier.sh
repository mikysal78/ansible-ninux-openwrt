#!/bin/sh
# Lanciato da watchcat (mode run_script) quando l'hub ZeroTier non risponde.
# 1) riavvia le interfacce netifd di ZeroTier (device owzt*/zt*);
# 2) se l'hub resta irraggiungibile, riavvia il servizio zerotier.
# Il ping deve uscire dal device ZeroTier (option interface di watchcat): con
# ZeroTier giu' Babel instrada 10.27.255.0/24 sulla mesh e l'hub risponde lo
# stesso.

TAG=zerotier-recover
HUB=$(uci -q get watchcat.@watchcat[0].pinghosts | awk '{print $1}')
DEV=$(uci -q get watchcat.@watchcat[0].interface)
WAIT=30

hub_ok() {
	[ -n "$HUB" ] && ping ${DEV:+-I "$DEV"} -c 3 -W 2 "$HUB" >/dev/null 2>&1
}

IFACES=$(uci -q show network | grep -E "^network\.[^.]+\.device='(owzt|zt)" | cut -d. -f2)

if [ -n "$IFACES" ]; then
	for i in $IFACES; do
		logger -t "$TAG" "hub $HUB irraggiungibile: riavvio interfaccia $i"
		ifdown "$i"
		sleep 2
		ifup "$i"
	done
	sleep "$WAIT"
	if hub_ok; then
		logger -t "$TAG" "hub $HUB di nuovo raggiungibile dopo il riavvio dell'interfaccia"
		exit 0
	fi
fi

logger -t "$TAG" "hub $HUB ancora irraggiungibile: riavvio il servizio zerotier"
/etc/init.d/zerotier restart
sleep "$WAIT"
if hub_ok; then
	logger -t "$TAG" "hub $HUB di nuovo raggiungibile dopo il riavvio di zerotier"
else
	logger -t "$TAG" "hub $HUB ancora irraggiungibile dopo il riavvio di zerotier"
fi
