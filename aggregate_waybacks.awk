NR==1 { cur_way=sanitize($1);cur_hits=$2; }
NR>1 {  
  if (cur_way == sanitize($1)) {
    cur_hits += $2;
  } else {
    print cur_way,cur_hits;
    cur_way=sanitize($1);
    cur_hits=$2;
  } 
}
END {
  print cur_way,cur_hits;
}
function sanitize( str ){
  if( str ~ /\/$/ ){
    return substr(str, 1, length(str)-1)
  }
  return str
}
