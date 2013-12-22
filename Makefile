# <variables>
CUSTOM_PIP_INDEX=localshop
export PYTHONPATH=`pwd`
export MYSQL_URI=mysql://root@localhost/markmentio
export REDIS_URI=redis://localhost:6379
export LOGLEVEL=DEBUG
# </variables>

all: test

prepare:
	@pip install -q curdling
	@curd install -r development.txt

clean:
	find . -name *.pyc -delete

test-kind:
	@-echo 'create database if not exists markmentio_test ' | mysql -uroot
	@TESTING=true MARKMENTIO_DB=mysql://root@localhost/markmentio_test MARKMENTIO_SETTINGS_MODULE="tests.settings" PYTHONPATH="$(PYTHONPATH)" \
		nosetests --with-coverage --cover-package=markmentio --nologcapture --logging-clear-handlers --stop --verbosity=2 -s tests/$(kind)

unit:
	@make test-kind kind=unit
functional:
	@make test-kind kind=functional

test: unit functional


shell:
	@PYTHONPATH=`pwd` ./markmentio/bin.py shell

release:
	@./.release
	@make publish


publish:
	@if [ -e "$$HOME/.pypirc" ]; then \
		echo "Uploading to '$(CUSTOM_PIP_INDEX)'"; \
		python setup.py register -r "$(CUSTOM_PIP_INDEX)"; \
		python setup.py sdist upload -r "$(CUSTOM_PIP_INDEX)"; \
	else \
		echo "You should create a file called \`.pypirc' under your home dir.\n"; \
		echo "That's the right place to configure \`pypi' repos.\n"; \
		echo "Read more about it here: https://github.com/Yipit/yipit/blob/dev/docs/rfc/RFC00007-python-packages.md"; \
		exit 1; \
	fi

run:
	@PYTHONPATH=`pwd` gunicorn -w 1 -b 127.0.0.1:5000 -k socketio.sgunicorn.GeventSocketIOWorker markmentio.server:app

check:
	@PYTHONPATH=`pwd` ./markmentio/bin.py check


local-migrate-forward:
	@[ "$(reset)" == "yes" ] && echo "drop database markmentio;create database markmentio" | mysql -uroot || echo "Running new migrations..."
	@alembic upgrade head

migrate-forward:
	echo "Running new migrations..."
	@alembic -c alembic.prod.ini upgrade head

local-migrate-back:
	@alembic downgrade -1

production-dump.sql:
	@printf "Getting production dump... "
	@mysqldump -u markmentio --password='VQ6org_czHEf4KW8' -hmarkmentio.cxnfdtrmcm7x.us-east-1.rds.amazonaws.com markment_prod > production-dump.sql
	@echo "OK"
	@echo "Saved at production-dump.sql"

deploy:
	@fab -i .conf/markment-prod.pem -u ubuntu -H markment.io deploy

create-machine:
	@fab -i .conf/markment-prod.pem -u ubuntu -H markment.io create

full-deploy: create-machine deploy

sync:
	@git push
	@make deploy

workers:
	@python markmentio/bin.py workers

enqueue-test:
	@python markmentio/bin.py enqueue

redis-dump:
	@scp -i .conf/markment-prod.pem ubuntu@markment.io:/var/lib/redis/*  /usr/local/var/db/redis/

tail:
	@ssh -i .conf/markment-prod.pem -t ubuntu@markment.io screen -c /srv/markment-io/.screenrc

ssh:
	@ssh -i .conf/markment-prod.pem ubuntu@markment.io
