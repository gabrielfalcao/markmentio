from flask.ext.assets import Environment, Bundle, ManageAssets


__all__ = 'manager',


class AssetsManager(object):

    def __init__(self, app):
        self.app = app
        self.env = Environment(app)
        self.env.url = app.static_url_path
        self.env.load_path.append(self.env.get_directory())
        self.env.set_directory(None)

    def create_bundles(self):
        """Create static bundles and bind them to the `app`

        We are using flask-assets to manage our static stuff, so we just
        need to create named bundles that includes our css and js files.

        Currently, we have just two bundles: `main_css` and `main_js`.
        """
        self.env.register(
            'js-all',
            Bundle('static/js/*.js', filters='jsmin', output='main.js'))

        self.env.register(
            'css-all',
            Bundle('static/css/*.css', filters='cssmin'),
            output='screen.css')

    def create_assets_command(self, manager):
        """Create the `assets` command in Flask-Script
        """
        manager.add_command('assets', ManageAssets(self.env))
