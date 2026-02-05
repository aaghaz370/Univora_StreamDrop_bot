@echo off
echo STARTING UNIVORA SECURE TUNNEL...
echo ---------------------------------------------------
echo This will create a temporary public HTTPS URL for your bot.
echo You must update your .env file with this new URL to make downloads work perfectly.
echo ---------------------------------------------------
echo Waiting for tunnel...
ssh -R 80:localhost:9091 nokey@localhost.run
pause
