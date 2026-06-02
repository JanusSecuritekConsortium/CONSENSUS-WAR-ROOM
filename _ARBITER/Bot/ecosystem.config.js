
module.exports = {
  apps: [{
    name: "aurelius-telegram",
    script: "aurelius_bot.py",
    cwd: __dirname,
    interpreter: "python",
    watch: false
  }]
}
