#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import redis


from functools import partial
import sqlalchemy as db


from sqlalchemy import (
    create_engine,
    MetaData,
)

from markmentio.settings import DATABASE

engine = create_engine(DATABASE)
metadata = MetaData()



class ORM(type):
    orm = {}

    def __init__(cls, name, bases, attrs):
        if not hasattr(cls, 'table'):
            return

        cls.__columns__ = {c.name: c.type.python_type
                           for c in cls.table.columns}

        super(ORM, cls).__init__(name, bases, attrs)

        if name not in ('ORM', 'Model'):
            ORM.orm[name] = cls

class Manager(object):

    def __init__(self, model_klass, engine):
        self.model = model_klass
        self.engine = engine

    def from_result_proxy(self, proxy, result):
        """Creates a new instance of the model given a sqlalchemy result proxy"""
        if not result:
            return None

        data = dict(zip(proxy.keys(), result))
        return self.model(engine=self.engine, **data)

    def execute(self, query):
        connection = self.get_connection()
        result = connection.execute(query)
        Models = partial(self.from_result_proxy, result)
        return map(Models, result.fetchall())

    def create(self, **data):
        """Creates a new model and saves it to MySQL"""
        instance = self.model(engine=self.engine, **data)
        return instance.save()

    def get_or_create(self, **data):
        """Tries to get a model from the database that would match the
        given keyword-args through `Model.find_one_by()`. If not
        found, a new instance is created in the database through
        `Model.create()`"""
        instance = self.find_one_by(**data)
        if not instance:
            instance = self.create(**data)

        return instance

    def query_by(self, order_by=None, **kw):
        """Queries the table with the given keyword-args and
        optionally a single order_by field.  This method is used
        internally and is not consistent with the other ORM methods by
        not returning a model instance.
        """
        conn = self.get_connection()
        query = self.model.table.select()
        for field, value in kw.items():
            query = query.where(getattr(self.model.table.c, field) == value)

        proxy = conn.execute(query.order_by(db.desc(getattr(self.model.table.c, order_by or 'id'))))
        return proxy

    def find_one_by(self, **kw):
        """Find a single model that could be found in the database and
        match all the given keyword-arguments"""
        proxy = self.query_by(**kw)
        return self.from_result_proxy(proxy, proxy.fetchone())

    def find_by(self, **kw):
        """Find a list of models that could be found in the database
        and match all the given keyword-arguments"""
        proxy = self.query_by(**kw)
        Models = partial(self.from_result_proxy, proxy)
        return map(Models, proxy.fetchall())

    def all(self):
        """Returns all existing rows as Model markmentio"""
        return self.find_by()

    def get_connection(self):
        return self.engine.connect()

    def insert_in_bulk(self, items):
        total_items = len(items)

        conn = self.get_connection()
        res = conn.execute(self.model.table.insert(), items)
        conn.close()
        return res


class Model(object):
    __metaclass__ = ORM

    manager = Manager

    @classmethod
    def using(cls, engine):
        return cls.manager(cls, engine)

    create = classmethod(lambda cls, **data: cls.using(engine).create(**data))
    get_or_create = classmethod(lambda cls, **data: cls.using(engine).get_or_create(**data))
    query_by = classmethod(lambda cls, order_by=None, **kw: cls.using(engine).query_by(order_by, **kw))
    find_one_by = classmethod(lambda cls, **kw: cls.using(engine).find_one_by(**kw))
    find_by = classmethod(lambda cls, **kw: cls.using(engine).find_by(**kw))
    all = classmethod(lambda cls: cls.using(engine).all())
    insert_in_bulk = classmethod(lambda cls, items: cls.using(engine).insert_in_bulk(items))


    def __init__(self, engine=None, **data):
        '''A Model can be instantiated with keyword-arguments that
        have the same keys as the declared fields, it will make a new
        model instance that is ready to be persited in the database.

        DO NOT overwrite the __init__ method of your custom model.

        There are 2 possibilities of customization of your model in
        construction time:

        * Implement a `preprocess(self, data)` method in your model,
        this method takes the dictionary that has the
        keyword-arguments given to the constructor and should return a
        dictionary with that data "post-processed" This ORM provides
        the handy optional method `initialize` that is always called
        in the end of the constructor.

        * Implement the `initialize(self)` method that will be always
          called after successfully creating a new model instance.
        '''
        Model = self.__class__
        module = Model.__module__
        name = Model.__name__
        columns = self.__columns__.keys()
        preprocessed_data = self.preprocess(data)
        if not isinstance(preprocessed_data, dict):
            raise InvalidModelDeclaration(
                'The model `{0}` declares a preprocess method but '
                'it does not return a dictionary!'.format(name))

        self.__data__ = preprocessed_data

        self.engine = engine

        for k, v in data.iteritems():
            if k not in self.__columns__:
                msg = "{0} is not a valid column name for the model {2}.{1} ({3})"
                raise InvalidColumnName(msg.format(k, name, module, columns))

            setattr(self, k, v)

        self.initialize()

    def __repr__(self):
        return '<{0} id={1}>'.format(self.__class__.__name__, self.id)

    def preprocess(self, data):
        """Placeholder for your own custom preprocess method, remember
        it must return a dictionary"""
        return data

    def _ensure_right_type(self, attr, value):
        data_type = self.__columns__.get(attr, None)
        if not value:
            return value

        if data_type and not isinstance(value, data_type):
            return data_type(value)

        return value

    def __setattr__(self, attr, value):
        if attr in self.__columns__:
            self.__data__[attr] = self._ensure_right_type(attr, value)
            return

        return super(Model, self).__setattr__(attr, value)

    def to_dict(self):
        """Returns the model values as a new dictionary"""
        keys = self.table.columns.keys()
        return dict([(k, v) for k, v in self.__data__.iteritems() if k in keys])

    def to_json(self):
        """Grabs the dictionary with the current model state returned
        by `to_dict` and serializes it to JSON"""
        return json.dumps(self.to_dict())

    def __getattr__(self, attr):
        if attr in self.__columns__.keys():
            value = self.__data__.get(attr, None)
            return self._ensure_right_type(attr, value)

        return super(Model, self).__getattribute__(attr)

    def delete(self):
        """Deletes the current model from the database (removes a row
        that has the given model primary key)
        """

        conn = self.get_engine().connect()

        return conn.execute(self.table.delete().where(
            self.table.c.id == self.id))

    @property
    def is_persisted(self):
        return 'id' in self.__data__

    def get_engine(self, input_engine=None):

        if not self.engine and not input_engine:
            raise EngineNotSpecified(
                "You must specify a SQLAlchemy engine object in order to "
                "delete this model instance.")
        elif self.engine and input_engine:
            raise MultipleEnginesSpecified(
                "This model instance has a SQLAlchemy engine object already. "
                "You may not save it to another engine.")

        return self.engine or input_engine

    def save(self, input_engine=None):
        """Persists the model instance in the DB.  It takes care of
        checking whether it already exists and should be just updated
        or if a new record should be created.
        """

        conn = self.get_engine(input_engine).connect()

        mid = self.__data__.get('id', None)
        if not mid:
            res = conn.execute(
                self.table.insert().values(**self.to_dict()))
            self.__data__['id'] = res.lastrowid
            self.__data__.update(res.last_inserted_params())
        else:
            res = conn.execute(
                self.table.update().values(**self.to_dict()).where(self.table.c.id == mid))
            self.__data__.update(res.last_updated_params())

        return self

    def get(self, name, fallback=None):
        """Get a field value from the model"""
        return self.__data__.get(name, fallback)

    def initialize(self):
        """Dummy method to be optionally overwritten in the subclasses"""

    def __eq__(self, other):
        """Just making sure models are comparable to each other"""
        if self.id and other.id:
            return self.id == other.id

        keys = set(self.__data__.keys() + other.__data__.keys())

        return all(
            [self.__data__.get(key) == other.__data__.get(key)
            for key in keys if key != 'id'])


class MultipleEnginesSpecified(Exception):
    pass


class EngineNotSpecified(Exception):
    pass


class InvalidColumnName(Exception):
    pass


class InvalidModelDeclaration(Exception):
    pass


class RecordNotFound(Exception):
    pass


models = ORM.orm
