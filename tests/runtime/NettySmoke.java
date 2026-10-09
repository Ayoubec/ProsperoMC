package org.prosperomc;
import io.netty.bootstrap.ServerBootstrap;
import io.netty.channel.*;
import io.netty.channel.nio.NioEventLoopGroup;
import io.netty.channel.socket.SocketChannel;
import io.netty.channel.socket.nio.NioServerSocketChannel;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import io.netty.util.ReferenceCountUtil;
import java.net.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;

public final class NettySmoke {
    public static void main(String[] args)throws Exception {
        if(args.length>0) {
            System.out.println(NettyCompat.prepare(Paths.get(args[0]),Arrays.asList(Paths.get(args[1]))));
            return;
        }
        EventLoopGroup group=new NioEventLoopGroup(1);
        Channel listener=null;
        try {
            listener=new ServerBootstrap().group(group).channel(NioServerSocketChannel.class)
                .childHandler(new ChannelInitializer<SocketChannel>() {
                    protected void initChannel(SocketChannel channel) {
                        channel.pipeline().addLast(new ChannelInboundHandlerAdapter() {
                            public void channelRead(ChannelHandlerContext context,Object message) {
                                try {
                                    if(((ByteBuf)message).readByte()!=42)throw new AssertionError("request");
                                    context.writeAndFlush(Unpooled.wrappedBuffer(new byte[]{77}));
                                } finally {ReferenceCountUtil.release(message);}
                            }
                        });
                    }
                }).bind(InetAddress.getByAddress(new byte[]{127,0,0,1}),0).sync().channel();
            try(Socket client=new Socket()) {
                client.connect(listener.localAddress(),3000);client.setSoTimeout(3000);
                client.getOutputStream().write(42);
                if(client.getInputStream().read()!=77)throw new AssertionError("reply");
            }
            if(MockNetworkInterfaces.calls!=1)throw new AssertionError("missing adapter error fixture");
            System.out.println("PASS: adapter Error fallback, NIO listener, TCP request/reply");
        } finally {
            if(listener!=null)listener.close().sync();
            group.shutdownGracefully(0,1,TimeUnit.SECONDS).sync();
        }
    }
}
