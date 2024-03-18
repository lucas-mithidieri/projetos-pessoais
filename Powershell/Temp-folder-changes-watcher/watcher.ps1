Function RunMyStuff {
    # Esta é a parte que você deseja que aconteça quando o arquivo for alterado
}

Function Watch {    
    $global:FolderCreated = $false
    $folder = "C:\Users\Lucas\AppData\Local\Temp"
    $filter = "*.*"

    # Cria o FileSystemWatcher
    $watcher = New-Object IO.FileSystemWatcher $folder, $filter -Property @{ 
        IncludeSubdirectories = $true
        EnableRaisingEvents = $true
    }

    # Define a ação a ser executada quando ocorrer um evento
    $action = {
        $global:FileChanged = $true
        $global:FolderCreated = $true
    }

    # Registra os eventos
    Register-ObjectEvent -InputObject $watcher -EventName Changed -Action $action
    Register-ObjectEvent -InputObject $watcher -EventName Created -Action $action

    while ($true) {
        while (-not ($global:FileChanged -or $global:FolderCreated)) {
            Start-Sleep -Milliseconds 100
        }

        # Verifica se um arquivo foi alterado
        if ($global:FileChanged -eq $true) {
            RunMyStuff
            $global:FileChanged = $false
        }

        # Verifica se uma pasta foi criada
        if ($global:FolderCreated -eq $true) {
            # Obtém a pasta mais recentemente criada
            $newFolder = Get-ChildItem $folder | Where-Object { $_.PSIsContainer } | Sort-Object CreationTime -Descending | Select-Object -First 1
            if ($newFolder -ne $null) {
                # Usa o próprio nome da pasta
                $newFolderName = $newFolder.Name
                Write-Host "Nova pasta criada: $($newFolderName)"
            }
            $global:FolderCreated = $false
        }
    }

    # Limpa os eventos quando a execução do script termina
    Unregister-Event -SourceIdentifier ($watcher | Get-Member -Name 'Event').Definition
}

RunMyStuff
Watch
