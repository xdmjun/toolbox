param()

$context = $env:ATOMCODE_HOOK_CONTEXT

$dangerPatterns = @(
    'rm -rf',
    'rm -r -f',
    'rm --recursive',
    'git reset --hard',
    'git checkout \.',
    'git checkout -- ',
    'git clean -f',
    'git clean -fd',
    'git restore \.',
    'del /F /S',
    'rd /s /q',
    'rmdir /s /q',
    'format ',
    'dd if=',
    '> /dev/sd'
)

foreach ($pattern in $dangerPatterns) {
    if ($context -match [regex]::Escape($pattern)) {
        Write-Output @"
{"action":"block","reason":"鉀?鍗遍櫓鎿嶄綔琚嫤鎴細`"$pattern`" 鍙兘閫犳垚鏁版嵁涓㈠け锛岃鐢ㄦ埛纭鍚庡啀鎵ц銆?}
"@
        exit 0
    }
}

Write-Output '{"action":"allow"}'
exit 0
