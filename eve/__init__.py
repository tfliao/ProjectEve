__desc__ = 'eve system commands'

__all__ = ['cmdbase', 'databae', 'common', 'polling_service']
__classmap__ = {
        'polling_service': 'PollingServiceCLI',
        }
__alias__ = {
    'ps': 'polling_service'
}

