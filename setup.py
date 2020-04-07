import os
import os.path

from setuptools import setup, Extension
import versioneer

# Default description in markdown
LONG_DESCRIPTION = open('README.md').read()


PKG_NAME     = 'azotea'
AUTHOR       = 'Jaime Zamorano'
AUTHOR_EMAIL = 'jzamoran@ucm.es'
DESCRIPTION  = 'command line tool to reduce DSLR RAW images',
LICENSE      = 'MIT'
KEYWORDS     = 'Astronomy Python LightPollution'
URL          = 'https://guaix.ucm.es/AZOTEA'
PACKAGES     = ["azotea"]
DEPENDENCIES = [
                  'tabulate',
                  'numpy',
                  'matplotlib',
                  'rawpy',
                  'exifread',
                  'opencv-python',
                  'jdcal'
]

CLASSIFIERS  = [
    'Environment :: Console',
    'Intended Audience :: Science/Research',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.6',
    'Topic :: Scientific/Engineering :: Astronomy',
    'Topic :: Scientific/Engineering :: Atmospheric Science',
    'Development Status :: 4 - Beta',
]

# Additional data inside the package
PACKAGE_DATA = {
    'azotea': [
                'data/camera.ini',
                'data/azotea.ini',
                'data/sql/*.sql',
                'data/sql/data/*.sql',
              ],
}

SCRIPTS = [
    'files/azotea'
]



setup(
    name             = PKG_NAME,
    version          = versioneer.get_version(),
    cmdclass         = versioneer.get_cmdclass(),
    author           = AUTHOR,
    author_email     = AUTHOR_EMAIL,
    description      = DESCRIPTION,
    long_description_content_type = "text/markdown",
    long_description = LONG_DESCRIPTION,
    license          = LICENSE,
    keywords         = KEYWORDS,
    url              = URL,
    classifiers      = CLASSIFIERS,
    packages         = PACKAGES,
    install_requires = DEPENDENCIES,
    package_data     = PACKAGE_DATA,
    scripts          = SCRIPTS
)
 
