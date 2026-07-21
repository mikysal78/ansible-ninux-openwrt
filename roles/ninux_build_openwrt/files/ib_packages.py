#!/usr/bin/env python3
"""Calcola la lista PACKAGES da passare a `make image` dell'ImageBuilder.

L'ImageBuilder non compila nulla: installa pacchetti gia' presenti nel suo
repository. La selezione va quindi espressa come lista di nomi, non come
simboli kconfig. Questo script traduce i .config/.ext del repo (unica fonte
di verita' della composizione delle varianti) in quella lista.

  --add FILE...    i pacchetti di questi file vanno INSTALLATI
                   (CONFIG_PACKAGE_x=y|m  ->  "x")
                   le loro righe negative sono rimozioni ESPLICITE
                   (# CONFIG_PACKAGE_x is not set  ->  "-x")
  --del FILE...    estensioni compilate nel seed ma non volute in QUESTA
                   variante (es. zerotier.ext in una variante WireGuard):
                   i loro pacchetti diventano rimozioni IMPLICITE.
  --valid FILE     .config del seed DOPO `make defconfig`: elenco autorevole
                   di cio' che esiste davvero nell'albero ed e' stato
                   compilato. Tutto cio' che non c'e' viene scartato, cosi'
                   `make image` non fallisce su un pacchetto inesistente.
  --keep-info FILE output di `make info` dell'ImageBuilder
  --profile NAME   profilo device, per leggere da --keep-info i pacchetti di
                   default del target.

Rimozioni esplicite e implicite non sono la stessa cosa. Un'estensione elenca
sia i propri pacchetti sia dipendenze che sono gia' default OpenWrt: uspot.ext
tira dentro firewall4, uhttpd e ucode. Negando l'estensione intera si
toglierebbero anche quelli, producendo un'immagine senza firewall. Le rimozioni
implicite vengono quindi filtrate contro i pacchetti di default del target.

Le rimozioni esplicite invece sopravvivono al filtro: sono una scelta
deliberata di chi ha scritto il .ext, e valgono anche contro un default (era
il caso di chilli.ext, che disattivava apposta firewall4 perche' coova-chilli
richiedeva iptables legacy).

--add vince su tutto: un pacchetto richiesto dalla variante resta installato.
"""

import argparse
import re
import sys

# CONFIG_PACKAGE_<nome>=y|m  oppure  # CONFIG_PACKAGE_<nome> is not set
RE_SET = re.compile(r"^CONFIG_PACKAGE_([^=\s]+)=([ym])\s*$")
RE_UNSET = re.compile(r"^#\s*CONFIG_PACKAGE_([^=\s]+) is not set\s*$")

# I nomi dei pacchetti OpenWrt sono minuscoli. Sotto CONFIG_PACKAGE_ vivono
# pero' anche opzioni di build interne a un pacchetto (CONFIG_PACKAGE_MAC80211_
# DEBUGFS, CONFIG_PACKAGE_MAC80211_MESH): passarle a `make image` come nomi di
# pacchetto lo farebbe fallire. Si riconoscono dal maiuscolo.
RE_PKGNAME = re.compile(r"^[a-z0-9][a-z0-9._+-]*$")


def parse_config(path):
    """Ritorna (installati, rimossi) leggendo un .config o un .ext."""
    installed, removed = set(), set()
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = RE_SET.match(line)
            if m:
                installed.add(m.group(1))
                continue
            m = RE_UNSET.match(line)
            if m:
                removed.add(m.group(1))
    return installed, removed


def parse_info(path, profile):
    """Pacchetti installati di default dall'ImageBuilder per questo profilo.

    Formato di `make info`:

        Default Packages: base-files ca-bundle dropbear ...
        Available Profiles:
        <profilo>:
            <descrizione>
            Packages: kmod-usb3 ...
    """
    defaults = set()
    in_profile = False
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("Default Packages:"):
                defaults |= set(line.split(":", 1)[1].split())
                continue
            if re.match(r"^\S+:\s*$", line):
                in_profile = line.split(":", 1)[0] == profile
                continue
            if in_profile and line.strip().startswith("Packages:"):
                defaults |= set(line.split(":", 1)[1].split())
    return defaults


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--add", nargs="*", default=[], metavar="FILE")
    ap.add_argument("--del", nargs="*", default=[], metavar="FILE", dest="delete")
    ap.add_argument("--valid", metavar="FILE")
    ap.add_argument("--keep-info", metavar="FILE")
    ap.add_argument("--profile", metavar="NAME")
    args = ap.parse_args()

    install, remove_explicit, remove_implicit = set(), set(), set()
    for path in args.add:
        i, r = parse_config(path)
        install |= i
        remove_explicit |= r
    for path in args.delete:
        i, _ = parse_config(path)
        remove_implicit |= i

    # Una variante che chiede un pacchetto vince su qualsiasi rimozione.
    remove_explicit -= install
    remove_implicit -= install | remove_explicit

    if args.keep_info and args.profile:
        keep = parse_info(args.keep_info, args.profile)
        spared = sorted(remove_implicit & keep)
        remove_implicit -= keep
        if spared:
            print(
                "ib_packages: non rimossi (default del target): " + " ".join(spared),
                file=sys.stderr,
            )

    remove = remove_explicit | remove_implicit
    install = {p for p in install if RE_PKGNAME.match(p)}
    remove = {p for p in remove if RE_PKGNAME.match(p)}

    if args.valid:
        built, _ = parse_config(args.valid)
        dropped = sorted((install | remove) - built)
        install &= built
        remove &= built
        if dropped:
            print(
                "ib_packages: ignorati (non compilati nel seed): " + " ".join(dropped),
                file=sys.stderr,
            )

    print(" ".join(sorted(install) + ["-" + p for p in sorted(remove)]))


if __name__ == "__main__":
    main()
