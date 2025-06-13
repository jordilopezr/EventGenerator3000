steps:
- task: UsePythonVersion@0
  displayName: 'Setting Python version to 3.10 as required by functions'
  inputs:
    versionSpec: '3.10.13'
    architecture: 'x64'

- bash: |
    # Instala las dependencias desde el archivo requirements.txt en la raíz del proyecto.
    pip install --target=".python_packages/lib/site-packages" -r "requirements.txt"
  displayName: 'Install Python dependencies'

- task: ArchiveFiles@2
  displayName: 'Archive files'
  inputs:
    # Empaqueta todo el contenido desde la raíz del directorio de trabajo.
    rootFolderOrFile: '$(System.DefaultWorkingDirectory)'
    
    # Excluye la carpeta raíz del zip, que es el comportamiento correcto.
    includeRootFolder: false
    
    archiveType: 'zip'
    archiveFile: '$(Build.ArtifactStagingDirectory)/$(Build.BuildId).zip'
    replaceExistingArchive: true

- task: PublishBuildArtifacts@1
  displayName: 'Publish a build artifact'
  inputs:
    PathtoPublish: '$(Build.ArtifactStagingDirectory)/$(Build.BuildId).zip'
    artifactName: 'drop'
