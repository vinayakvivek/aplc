DIR="150050098-150050100"
files=(
    "Parser.py"
    "lexer.py"
    "ast.py"
    "cfg.py"
)
mkdir -p $DIR
for i in ${files[@]}
do
  cp $i $DIR
done
tar -cvzf $DIR.tar.gz $DIR/
rm -rf $DIR