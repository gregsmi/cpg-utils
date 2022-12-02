#!/usr/bin/env python

from setuptools import find_packages, setup

setup(
    name='cpg-utils-ms',
    # This tag is automatically updated by bumpversion
    version='1.2.9',
    description='Library of convenience functions specific to the CPG (MS version)',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url=f'https://github.com/gregsmi/cpg-utils',
    license='MIT',
    packages=find_packages(),
    install_requires=[
        'google-auth>=1.27.0',
        'google-cloud-secret-manager',
        'azure-identity',
        'azure-keyvault-secrets',
        'azure-storage-blob',
        'cloudpathlib[all]',
        'hail',
        'toml',
        'frozendict',
    ],
    extras_require={
        'test': [
            'pytest',
            'pytest-mock',
            'pytest-cov'
        ],
    },
    keywords='bioinformatics',
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
    ],
)
