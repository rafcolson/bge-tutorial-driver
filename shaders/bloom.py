uniform sampler2D bgl_RenderedTexture;

void main()
{
vec4 sum = vec4(0);
vec2 texcoord = vec2(gl_TexCoord[0]).st;
int j;
int i;


for( i= -4 ;i < 4; i++)
{
for (j = -4; j < 4; j++)
{
sum += texture2D(bgl_RenderedTexture, texcoord + vec2(j, i)*0.0045) * 0.125; 
}
}


gl_FragColor = sum*sum*0.00390625+texture2D(bgl_RenderedTexture, texcoord);
}