# Set your R2 access and secret keys
$env:AWS_ACCESS_KEY_ID = "68aef73bf4a4456fa1aaa108b394e6f4"
$env:AWS_SECRET_ACCESS_KEY = "ad62471acbff9a10da6428c5a7553c7cbaca5e22b8836f342fd02647ba82fe97"
$env:AWS_DEFAULT_REGION = "eeur"

# Your R2 endpoint
$endpoint = "https://38e42d66aea00f4e35692f08923b2e6b.r2.cloudflarestorage.com"
$bucket = "ragpilot-documents"

# List of object IDs (with trailing slash if needed)
$objectIDs = @(
    "235673c9-9ef5-47e5-8551-9d3a516af83c/",
    "367b28a1-911f-453f-9e91-afb522b125c5/",
    "3813056c-670a-43c8-9b8a-853fb8f6b6dc/",
    "63d661d0-348e-4cad-91d7-d933f28658b5/",
    "b3612050-2f91-43ed-afa0-e9ad6e265795/",
    "c36148dd-85c0-4c1f-b555-ce93dd4e59fe/",
    "e66f3d05-dde9-4bac-b944-9aeb50cf8597/"
)

# Loop through the list and delete each object
foreach ($objectID in $objectIDs) {
    $fullKey = "documents/$objectID"
    Write-Host "Deleting: $fullKey"
    aws --endpoint-url $endpoint s3 rm "s3://$bucket/$bucket/$fullKey" --recursive
}
# Optional: Cleanup
# Remove-Item Env:\AWS_ACCESS_KEY_ID
# Remove-Item Env:\AWS_SECRET_ACCESS_KEY
# Remove-Item Env:\AWS_DEFAULT_REGION

Write-Host "All deletions complete."
