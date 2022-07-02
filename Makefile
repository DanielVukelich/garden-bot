
mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
current_dir := $(dir $(mkfile_path))

.PHONY: setup install uninstall

setup: venv/touched

venv/touched:
	test -d venv || python3 -m virtualenv venv
	venv/bin/python3 -m pip install -r requirements.txt
	touch venv/touched

install: setup
	id -u garden-www >/dev/null 2>&1 || useradd garden-www -G gpio,video
	test -d /usr/bin/garden-bot || ln -s $(current_dir) /usr/bin/garden-bot
	test -L /etc/systemd/system/garden-bot.service || ln -s $(current_dir)/garden-bot.service /etc/systemd/system/garden-bot.service
	systemctl enable garden-bot
	systemctl start garden-bot

uninstall:
	systemctl stop garden-bot
	systemctl disable garden-bot
	rm /usr/bin/garden-bot
	userdel garden-www
