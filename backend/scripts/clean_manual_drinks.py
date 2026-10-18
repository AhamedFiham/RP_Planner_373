"""Clean manually collected Drinks class folders without editing raw images."""
from clean_manual_fruits import clean_manual_dataset


def clean_manual_drinks():
    clean_manual_dataset('Drinks', 'manual_drinks_classification')


if __name__ == '__main__':
    clean_manual_drinks()
