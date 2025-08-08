"""Setup script for Screen Translator v2.0"""

import sys
from setuptools import setup, find_packages

# Python version check
if sys.version_info < (3, 8):
    sys.exit('Screen Translator requires Python 3.8 or higher')

# Read requirements based on Python version
def read_requirements():
    """Read requirements with Python version compatibility"""
    requirements = []
    
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # Handle conditional requirements
                if '; python_version' in line:
                    # Let pip handle conditional requirements
                    requirements.append(line)
                else:
                    requirements.append(line)
    
    return requirements

# Additional requirements for different Python versions
python_version_specific = {
    '>=3.8,<3.11': [
        'opencv-python>=4.8.0.76',
        'numba>=0.57.1',
    ],
    '>=3.11,<3.13': [
        'opencv-python>=4.8.0.76',
        'numpy>=1.26.0,<2.0.0',
    ],
    '>=3.13': [
        'numpy>=1.26.0',
        'httpx>=0.25.0',
    ]
}

setup(
    name='screen-translator',
    version='2.0.0',
    description='Advanced screen translation tool with OCR and TTS',
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    author='Screen Translator Team',
    python_requires='>=3.8',
    packages=find_packages(include=['src', 'src.*']),
    install_requires=read_requirements(),
    extras_require={
        'dev': [
            'pytest>=7.4.0',
            'pytest-cov>=4.1.0',
            'pytest-mock>=3.11.1',
            'black>=23.7.0',
            'isort>=5.12.0',
            'flake8>=6.1.0',
            'mypy>=1.5.0',
        ],
        'build': [
            'pyinstaller>=5.13.2',
            'wheel>=0.41.2',
            'setuptools>=68.1.2',
        ],
        'performance': [
            'numba>=0.57.1; python_version < "3.12"',
            'cython>=3.0.0; python_version < "3.13"',
        ]
    },
    entry_points={
        'console_scripts': [
            'screen-translator=src.main:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Operating System :: OS Independent',
        'Topic :: Multimedia :: Graphics :: Capture :: Screen Capture',
        'Topic :: Text Processing :: Linguistic',
    ],
    keywords='screen capture, OCR, translation, accessibility, automation',
    project_urls={
        'Source': 'https://github.com/screen-translator/screen-translator',
        'Bug Reports': 'https://github.com/screen-translator/screen-translator/issues',
        'Documentation': 'https://screen-translator.readthedocs.io/',
    }
)