from setuptools import setup

setup(name='RedDrum-Aggregator',
      version='0.5.5',
      description='A python Redfish Service Aggregator for a rack of monolythic servers with Redfish.',
      author='RedDrum-Redfish-Project / Alaa Yousif and Paul Vancil, Dell ESI',
      author_email='redDrumRedfishProject@gmail.com',
      license='BSD License',
      classifiers=[
          'Development Status :: 4 - Beta',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Python :: 3.4',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: Software Development :: Libraries :: Embedded Systems',
          'Topic :: Communications'
      ],
      keywords='Redfish RedDrum SPMF Aggregator ',
      url='https://github.com/RedDrum-Redfish-Project/RedDrum-Aggregator',
      download_url='https://github.com/RedDrum-Redfish-Project/RedDrum-Aggregator/archive/0.5.5.tar.gz',
      packages=['reddrum_aggregator'],
      scripts=['scripts/redDrumAggregatorMain'],
      package_data={'reddrum_aggregator': ['getLinuxIpInfo.sh','getLinuxProtocolInfo.sh'] },
      install_requires=[
          'RedDrum-Frontend==0.9.5', # the common RedDrum Frontend code that has dependency on Flask
          'passlib==1.7.1',          # used by Frontend
          'Flask',                   # used by Frontend
          'pytz'                     # used by Frontend
          # obmc.mapper
          # dbus
      ],
)
