#
# kmod-wdat-wdt: watchdog hardware tramite la tabella ACPI WDAT.
#
# Sui Celeron Gemini Lake (J4125, router di confine ReginaMargherita116) il
# watchdog TCO non e' raggiungibile da Linux: lpc_ich non lo espone ("No MFD
# cells added") e i2c-i801 riconosce lo SMBus 0x31d4 senza FEATURE_TCO, quindi
# kmod-itco-wdt si carica ma non crea /dev/watchdog. Il BIOS pero' pubblica la
# tabella ACPI WDAT, gestita da wdat_wdt, che OpenWrt 25.12 non pacchettizza
# (CONFIG_WDAT_WDT non impostato in target/linux/generic/config-6.12).
#
# WDAT_WDT seleziona da solo WATCHDOG_CORE e ACPI_WATCHDOG (bool senza prompt):
# nessun simbolo nuovo resta senza valore in kconfig.
#
# NIENTE AUTOLOAD, di proposito: se la WDAT di un BIOS e' difettosa, caricare il
# modulo al boot (con procd che apre /dev/watchdog) manda il router in un ciclo
# di riavvii, irrecuperabile da remoto. Va provato a mano (modprobe wdat_wdt) e
# solo dopo abilitato al boot con un file in /etc/modules-boot.d/.
#

include $(TOPDIR)/rules.mk
include $(INCLUDE_DIR)/kernel.mk

PKG_NAME:=wdat-wdt
PKG_RELEASE:=1
PKG_LICENSE:=GPL-2.0-only

include $(INCLUDE_DIR)/package.mk

define KernelPackage/wdat-wdt
  SUBMENU:=Other modules
  TITLE:=ACPI Watchdog Action Table (WDAT) watchdog
  DEPENDS:=@TARGET_x86
  KCONFIG:= \
	CONFIG_WDAT_WDT \
	CONFIG_WATCHDOG_CORE=y
  FILES:=$(LINUX_DIR)/drivers/watchdog/wdat_wdt.ko
endef

define KernelPackage/wdat-wdt/description
  Watchdog hardware dei sistemi che pubblicano la tabella ACPI WDAT
  (es. Celeron Gemini Lake, dove iTCO_wdt non trova il TCO).
  Non viene caricato al boot: vedi il commento in testa al Makefile.
endef

# Modulo del kernel in-tree: lo compila il pacchetto linux, qui non c'e' nulla
define Build/Compile
endef

$(eval $(call KernelPackage,wdat-wdt))
