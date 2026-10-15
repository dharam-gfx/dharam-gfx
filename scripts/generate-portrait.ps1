$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

function Get-TextTargetPoints {
    param(
        [string]$Text,
        [string]$FontName,
        [single]$FontSize,
        [int]$Width,
        [int]$Height,
        [double]$FrameWidth,
        [double]$FrameHeight
    )

    $bitmap = [System.Drawing.Bitmap]::new($Width, $Height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $font = [System.Drawing.Font]::new($FontName, $FontSize, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
    $brush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::White)
    $format = [System.Drawing.StringFormat]::new()
    $format.Alignment = [System.Drawing.StringAlignment]::Center
    $format.LineAlignment = [System.Drawing.StringAlignment]::Center
    $graphics.Clear([System.Drawing.Color]::Black)
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $graphics.DrawString($Text, $font, $brush, [System.Drawing.RectangleF]::new(0, 0, $Width, $Height), $format)

    $points = [System.Collections.Generic.List[object]]::new()
    for ($y = 0; $y -lt $Height; $y++) {
        for ($x = 0; $x -lt $Width; $x++) {
            if ($bitmap.GetPixel($x, $y).R -gt 64) {
                $points.Add([pscustomobject]@{
                    X = 59.0 + ($x + 0.5) * $FrameWidth / $Width
                    Y = 126.0 + ($y + 0.5) * $FrameHeight / $Height
                })
            }
        }
    }

    $graphics.Dispose()
    $font.Dispose()
    $brush.Dispose()
    $format.Dispose()
    $bitmap.Dispose()
    return $points.ToArray()
}

$root = Split-Path -Parent $PSScriptRoot
$sourcePath = Join-Path $root "assets\source\dharam.png"
if (-not (Test-Path -LiteralPath $sourcePath)) {
    throw "Portrait image not found: $sourcePath"
}

$bitmap = [System.Drawing.Bitmap]::new($sourcePath)
try {
    $frameWidth = 342.0
    $frameHeight = 354.0
    $columns = 150
    $rows = [int][Math]::Round($columns * $frameHeight / $frameWidth)
    $cropWidth = $bitmap.Width
    $cropHeight = [Math]::Min($bitmap.Height, [int][Math]::Round($cropWidth * $frameHeight / $frameWidth))
    $darkLow = @(47, 101, 139)
    $darkHigh = @(205, 250, 255)
    $lightLow = @(52, 82, 102)
    $lightHigh = @(8, 126, 139)
    $targets = @{
        "JS" = @(Get-TextTargetPoints -Text "JS" -FontName "Arial" -FontSize 55 -Width $columns -Height $rows -FrameWidth $frameWidth -FrameHeight $frameHeight)
        "TS" = @(Get-TextTargetPoints -Text "TS" -FontName "Arial" -FontSize 55 -Width $columns -Height $rows -FrameWidth $frameWidth -FrameHeight $frameHeight)
        "CODE" = @(Get-TextTargetPoints -Text "</>" -FontName "Consolas" -FontSize 39 -Width $columns -Height $rows -FrameWidth $frameWidth -FrameHeight $frameHeight)
    }
    $keyTimes = "0;0.2113;0.303;0.4437;0.5352;0.6761;0.7676;0.9085;1"
    $travellerCount = 900

    foreach ($theme in @("dark", "light")) {
        if ($theme -eq "dark") {
            $low = $darkLow
            $high = $darkHigh
        }
        else {
            $low = $lightLow
            $high = $lightHigh
        }

        $portraitDots = [System.Text.StringBuilder]::new()
        $travellerDots = [System.Text.StringBuilder]::new()
        $portraitPoints = [System.Collections.Generic.List[object]]::new()
        $dotCount = 0
        for ($row = 0; $row -lt $rows; $row++) {
            $sourceY = [Math]::Min($cropHeight - 1, [int](($row + 0.5) * $cropHeight / $rows))
            for ($column = 0; $column -lt $columns; $column++) {
                $sourceX = [Math]::Min($cropWidth - 1, [int](($column + 0.5) * $cropWidth / $columns))
                $pixel = $bitmap.GetPixel($sourceX, $sourceY)
                if ($pixel.A -lt 48) {
                    continue
                }

                $luminance = (0.2126 * $pixel.R + 0.7152 * $pixel.G + 0.0722 * $pixel.B) / 255.0
                if ($theme -eq "dark") {
                    $intensity = 0.3 + 0.7 * [Math]::Sqrt($luminance)
                }
                else {
                    $intensity = 1.0 - $luminance
                    if ($intensity -lt 0.18) {
                        continue
                    }
                }
                $channels = for ($channel = 0; $channel -lt 3; $channel++) {
                    [int][Math]::Round($low[$channel] + ($high[$channel] - $low[$channel]) * $intensity)
                }
                $color = "#{0:x2}{1:x2}{2:x2}" -f $channels[0], $channels[1], $channels[2]
                $x = 59.0 + ($column + 0.5) * $frameWidth / $columns
                $y = 126.0 + ($row + 0.5) * $frameHeight / $rows
                $radius = 0.2 + 0.35 * $intensity
                $opacity = 0.4 + 0.6 * $intensity
                $xText = $x.ToString("0.0", [Globalization.CultureInfo]::InvariantCulture)
                $yText = $y.ToString("0.0", [Globalization.CultureInfo]::InvariantCulture)
                $radiusText = $radius.ToString("0.00", [Globalization.CultureInfo]::InvariantCulture)
                $opacityText = $opacity.ToString("0.00", [Globalization.CultureInfo]::InvariantCulture)
                [void]$portraitDots.Append("<circle cx=`"$xText`" cy=`"$yText`" r=`"$radiusText`" fill=`"$color`" opacity=`"$opacityText`"/>")
                $portraitPoints.Add([pscustomobject]@{
                    X = $x
                    Y = $y
                    Radius = $radiusText
                    Opacity = $opacityText
                    Color = $color
                })
                $dotCount++
            }
        }

        $actualTravellerCount = [Math]::Min($travellerCount, $portraitPoints.Count)
        $pointInterval = $portraitPoints.Count / [double]$actualTravellerCount
        for ($travellerIndex = 0; $travellerIndex -lt $actualTravellerCount; $travellerIndex++) {
            $pointIndex = [int][Math]::Floor($travellerIndex * $pointInterval)
            $point = $portraitPoints[$pointIndex]
            $offsets = foreach ($symbol in @("JS", "TS", "CODE")) {
                    $symbolPoints = $targets[$symbol]
                    $symbolIndex = ($travellerIndex * 7919) % $symbolPoints.Count
                    $targetX = $symbolPoints[$symbolIndex].X
                    $targetY = $symbolPoints[$symbolIndex].Y
                    $offsetX = ($targetX - $point.X).ToString("0.0", [Globalization.CultureInfo]::InvariantCulture)
                    $offsetY = ($targetY - $point.Y).ToString("0.0", [Globalization.CultureInfo]::InvariantCulture)
                    "$offsetX $offsetY"
                }
            $animation = "<animateTransform attributeName=`"transform`" type=`"translate`" dur=`"14.2s`" repeatCount=`"indefinite`" calcMode=`"linear`" keyTimes=`"$keyTimes`" values=`"0 0;0 0;$($offsets[0]);$($offsets[0]);$($offsets[1]);$($offsets[1]);$($offsets[2]);$($offsets[2]);0 0`"/>"
            $opacityAnimation = "<animate attributeName=`"opacity`" dur=`"14.2s`" repeatCount=`"indefinite`" calcMode=`"linear`" keyTimes=`"$keyTimes`" values=`"0;0;0;$($point.Opacity);$($point.Opacity);$($point.Opacity);$($point.Opacity);$($point.Opacity);0`"/>"
            $xText = $point.X.ToString("0.0", [Globalization.CultureInfo]::InvariantCulture)
            $yText = $point.Y.ToString("0.0", [Globalization.CultureInfo]::InvariantCulture)
            [void]$travellerDots.Append("<circle cx=`"$xText`" cy=`"$yText`" r=`"$($point.Radius)`" fill=`"$($point.Color)`" opacity=`"0`">$animation$opacityAnimation</circle>")
        }

        $svgPath = Join-Path $root "assets\banner-$theme.svg"
        $svg = [System.IO.File]::ReadAllText($svgPath)
        $startMarker = "<!-- PORTRAIT_DOTS_START -->"
        $endMarker = "<!-- PORTRAIT_DOTS_END -->"
        $startIndex = $svg.IndexOf($startMarker, [StringComparison]::Ordinal)
        $endIndex = $svg.IndexOf($endMarker, $startIndex + $startMarker.Length, [StringComparison]::Ordinal)
        if ($startIndex -lt 0 -or $endIndex -lt 0) {
            throw "Portrait markers are missing from $svgPath"
        }

        $portraitAnimation = "<animate attributeName=`"opacity`" dur=`"14.2s`" repeatCount=`"indefinite`" calcMode=`"linear`" keyTimes=`"$keyTimes`" values=`"1;1;0;0;0;0;0;0;1`"/>"
        $replacement = "$startMarker<g aria-label=`"Dharam dot-matrix portrait`">$($portraitDots.ToString())$portraitAnimation</g><g aria-label=`"Morphing technology particles`">$($travellerDots.ToString())</g>$endMarker"
        $updated = $svg.Substring(0, $startIndex) + $replacement + $svg.Substring($endIndex + $endMarker.Length)
        [System.IO.File]::WriteAllText($svgPath, $updated, [System.Text.UTF8Encoding]::new($false))
        Write-Output "Generated $dotCount portrait dots in $svgPath"
    }
}
finally {
    $bitmap.Dispose()
}