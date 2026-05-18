.PHONY: run ssh test

run:
	ansible-playbook -i test_hosts.ini setup.yml

ssh:
	ssh-copy-id -p 2222 root@localhost

test:
	ansible-playbook -i test_hosts.ini setup.yml -k
