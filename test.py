from datetime import datetime

# Define the input date as a string
date_string = "01.02.2023"

# Define the date format
date_format = "%d.%m.%Y"

# Convert the date string to a datetime object
''' date_object = datetime.strptime(date_string, date_format) '''
date_object = datetime.strptime("2023-01-02")

# Convert the datetime object to a Unix timestamp in milliseconds
unix_timestamp = int(date_object.timestamp()) * 1000

print(unix_timestamp)